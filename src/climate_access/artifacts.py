"""Bounded NetCDF batches, exact readback, manifest-based resume and ZIP delivery."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
import numpy as np
import xarray as xr
from .config import DATASET, VARIABLES, Request
from .gee import validate_array


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''): h.update(block)
    return h.hexdigest()


def _json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


def _publish_no_replace(temporary, target):
    if os.name == 'nt':
        temporary.rename(target)  # Windows rename is atomic and refuses an existing target.
    else:
        os.link(temporary, target)


def _manifest(root, obj):
    target = root/'manifest.json'
    if target.is_symlink(): raise ValueError('Manifest symlinks are not supported')
    with tempfile.NamedTemporaryFile(dir=root, suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name); stream.write(_json_bytes(obj))
        stream.flush(); os.fsync(stream.fileno())
    try: temporary.replace(target)
    finally: temporary.unlink(missing_ok=True)


def _coords(req, times):
    return {'time': np.array(times, dtype='datetime64[ns]'),
            'latitude': req.area[0]-np.arange(req.height)*.25,
            'longitude': req.area[1]+np.arange(req.width)*.25}


def _check_dataset(ds, req, times):
    if set(ds.data_vars) != set(req.variables) or ds.attrs.get('source_dataset') != DATASET or ds.attrs.get('time_standard') != 'UTC':
        raise ValueError('NetCDF variables or provenance mismatch')
    coords = _coords(req, times)
    for name, expected in coords.items():
        if not np.array_equal(ds[name].values, expected): raise ValueError('NetCDF coordinate/time mismatch')
    for variable in req.variables:
        values = ds[variable].values
        if (ds[variable].dims != ('time', 'latitude', 'longitude') or values.dtype.kind != 'f' or
            values.dtype.itemsize not in (4, 8) or not np.isfinite(values).all() or
            (np.abs(values) >= 1e19).any() or ds[variable].attrs.get('units') != VARIABLES[variable]['units']):
            raise ValueError('NetCDF values, dimensions or units mismatch')


def _read(root, *, require_complete):
    manifest = root/'manifest.json'
    if manifest.is_symlink(): raise ValueError('Manifest symlinks are not supported')
    obj = json.loads(manifest.read_text(encoding='utf-8'))
    req = Request.from_dict(obj['request'])
    if obj.get('schema_version') != 1 or obj.get('source_dataset') != DATASET or obj.get('request_sha256') != req.fingerprint:
        raise ValueError('Manifest identity/provenance mismatch')
    files = obj.get('files')
    if not isinstance(files, list) or len(files) > len(req.batches) or obj.get('status') not in {'partial', 'complete'}:
        raise ValueError('Invalid batch manifest')
    if (require_complete or obj['status'] == 'complete') and (obj['status'] != 'complete' or len(files) != len(req.batches)):
        raise ValueError('Run is incomplete')
    for index, entry in enumerate(files):
        name = f'part-{index:05}.nc'
        if entry.get('name') != name: raise ValueError('Unexpected batch filename or ordering')
        path = root/name
        if path.is_symlink() or not path.is_file() or path.resolve().parent != root.resolve():
            raise ValueError('Missing batch or unsafe path')
        if path.stat().st_size != entry.get('bytes') or sha(path) != entry.get('sha256'):
            raise ValueError('Batch checksum mismatch')
        with xr.open_dataset(path, engine='h5netcdf') as ds:
            _check_dataset(ds, req, req.batches[index])
    if sum(entry['bytes'] for entry in files)+manifest.stat().st_size > req.max_output_mib*1024**2:
        raise ValueError('Artifacts exceed configured output budget')
    return req, obj


def verify_run(directory):
    root = Path(directory)
    req, obj = _read(root, require_complete=True)
    return dict(passed=True, dataset=DATASET, files=len(obj['files']), hours=len(req.timestamps),
                request_sha256=req.fingerprint, checks=['SHA256', 'UTC sequence', 'native coordinates',
                    'variables', 'units', 'finite values', 'output budget'],
                limitation='Consistency and provenance checks; not independent meteorological accuracy validation')


def _download(req, directory, fetcher):
    root = Path(directory)
    if root.is_symlink(): raise ValueError('Output directory symlinks are not supported')
    root.mkdir(parents=True, exist_ok=True)
    if (root/'manifest.json').exists():
        stored, obj = _read(root, require_complete=False)
        if stored.fingerprint != req.fingerprint: raise ValueError('Output belongs to a different request')
    else:
        if any(p.name != '.run.lock' for p in root.iterdir()): raise FileExistsError('Output directory is not an empty toolkit run')
        obj = dict(schema_version=1, source_dataset=DATASET, distribution='Google Earth Engine',
                   request=req.to_dict(), request_sha256=req.fingerprint, status='partial', files=[],
                   processing='Raw source-band values; no interpolation, clipping, deaccumulation or timezone conversion')
        _manifest(root, obj)
    for index in range(len(obj['files']), len(req.batches)):
        times = req.batches[index]
        expected_values = req.height*req.width*len(req.variables)*len(times)*8
        if shutil.disk_usage(root).free < 512*1024**2+expected_values*4:
            raise ValueError('Insufficient free space for batch plus 512 MiB reserve')
        if sum(x['bytes'] for x in obj['files'])+expected_values*2+128*1024 > req.max_output_mib*1024**2:
            raise ValueError('Insufficient output budget for next batch; no request made')
        target = root/f'part-{index:05}.nc'
        if target.exists() or target.is_symlink(): raise FileExistsError('Uncommitted batch exists; inspect it before retrying')
        array = validate_array(fetcher(req, times), req, times)
        values = {v: np.stack([array[f't{stamp:%Y%m%d%H}_{v}'] for stamp in times]) for v in req.variables}
        ds = xr.Dataset({v: (('time','latitude','longitude'), values[v],
                            {'units': VARIABLES[v]['units'], 'gee_band': VARIABLES[v]['band']}) for v in req.variables},
            coords=_coords(req, times), attrs=dict(source_dataset=DATASET, distribution='Google Earth Engine',
                time_standard='UTC', spatial_method='native 0.25 degree pixel centers; no aggregation',
                temporal_method='raw source bands; consult upstream accumulation conventions before statistics'))
        with tempfile.NamedTemporaryFile(dir=root, suffix='.nc.tmp', delete=False) as stream:
            temporary = Path(stream.name)
        try:
            ds.to_netcdf(temporary, engine='h5netcdf', encoding={v: {'zlib':True,'complevel':4,'_FillValue':None} for v in req.variables})
            with xr.open_dataset(temporary, engine='h5netcdf') as stored:
                _check_dataset(stored, req, times)
                for variable in req.variables:
                    if stored[variable].dtype != values[variable].dtype or not np.array_equal(stored[variable].values, values[variable]):
                        raise ValueError('NetCDF roundtrip changed source values or dtype')
            entry = dict(name=target.name, bytes=temporary.stat().st_size, sha256=sha(temporary), hours=len(times))
            next_obj = dict(obj, files=obj['files']+[entry],
                            status='complete' if index+1==len(req.batches) else 'partial')
            if sum(x['bytes'] for x in next_obj['files'])+len(_json_bytes(next_obj)) > req.max_output_mib*1024**2:
                raise ValueError('Actual output exceeds budget; batch was not published')
            _publish_no_replace(temporary, target)
            _manifest(root, next_obj)
            obj = next_obj
        finally:
            ds.close(); temporary.unlink(missing_ok=True)
    return verify_run(root)


def download(req, directory, fetcher):
    root = Path(directory)
    if root.is_symlink(): raise ValueError('Output directory symlinks are not supported')
    root.mkdir(parents=True, exist_ok=True)
    lock = root/'.run.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write('climate-data-access writer; inspect an interrupted run before removing this lock\n')
        stream.flush()
    try:
        return _download(req, root, fetcher)
    finally:
        lock.unlink()


def bundle(directory, destination):
    root, target = Path(directory).resolve(), Path(destination).resolve()
    verify_run(root)
    if target.is_relative_to(root): raise ValueError('Place ZIP outside the run directory')
    if target.exists(): raise FileExistsError(target.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    obj = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.zip.tmp', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name in ['manifest.json']+[entry['name'] for entry in obj['files']]: archive.write(root/name, name)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None: raise ValueError('ZIP CRC failed')
        _publish_no_replace(temporary, target)
    finally: temporary.unlink(missing_ok=True)
    return dict(passed=True, file=target.name, bytes=target.stat().st_size, sha256=sha(target), zip_crc_passed=True)
