"""Official-SDK GEE transport, with no credentials or project IDs in artifacts."""
import io
import time
import numpy as np
from .config import DATASET, VARIABLES


def validate_native_grid(asset, variables):
    bands = {band['id']: band for band in asset.get('bands', [])}
    expected = dict(scaleX=.25, scaleY=-.25, translateX=-180.125, translateY=90.125)
    for variable in variables:
        band = VARIABLES[variable]['band']
        grid = bands.get(band, {}).get('grid', {})
        transform = grid.get('affineTransform', {})
        if (grid.get('crsCode') != 'EPSG:4326' or
            any(transform.get(k) != v for k, v in expected.items()) or
            transform.get('shearX', 0) != 0 or transform.get('shearY', 0) != 0):
            raise ValueError('Source band missing or native ERA5 grid changed')


def validate_array(array, req, times):
    if not isinstance(array, np.ndarray) or array.shape != (req.height, req.width) or array.dtype.names != tuple(req.band_names(times)):
        raise ValueError('Response shape, band order or band names do not match request')
    for name in array.dtype.names:
        values = array[name]
        if values.dtype.kind != 'f' or values.dtype.itemsize not in (4, 8):
            raise ValueError('Expected float32/float64 source values')
        if not np.isfinite(values).all() or (np.abs(values) >= 1e19).any():
            raise ValueError('Response contains missing, nonfinite or sentinel-like values')
    for variable in req.variables:
        dtypes = {array[f't{stamp:%Y%m%d%H}_{variable}'].dtype.str for stamp in times}
        if len(dtypes) != 1:
            raise ValueError('Source dtype changed within the batch')
    return array


def decode_response(raw, req, times):
    if not isinstance(raw, bytes) or len(raw) > 40*1024**2:
        raise ValueError('Response is not bounded NPY bytes')
    try:
        array = np.load(io.BytesIO(raw), allow_pickle=False)
    except (ValueError, OSError, EOFError):
        raise ValueError('Invalid NPY response') from None
    return validate_array(array, req, times)


def _status(error):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        for candidate in (getattr(error, 'status_code', None),
                          getattr(getattr(error, 'resp', None), 'status', None),
                          getattr(getattr(error, 'response', None), 'status_code', None)):
            if isinstance(candidate, int): return candidate
        error = error.__cause__ or error.__context__
    return None


def retry_transient(operation, *, sleep=time.sleep):
    for attempt in range(3):
        try:
            return operation()
        except Exception as error:
            status = _status(error)
            if attempt < 2 and (status in {429, 500, 502, 503, 504} or isinstance(error, TimeoutError)):
                sleep(2**attempt)
                continue
            suffix = f' (HTTP {status})' if status is not None else ''
            raise RuntimeError('GEE request failed'+suffix+'; check access, availability and quotas') from None


class GEEClient:
    def __init__(self, project):
        if not isinstance(project, str) or not project.strip():
            raise ValueError('A user-owned Earth Engine project is required')
        try:
            import ee
        except ImportError:
            raise RuntimeError('Install the gee extra and configure Earth Engine authentication') from None
        try:
            ee.Initialize(project=project)
        except Exception:
            raise RuntimeError('GEE initialization failed; authenticate and configure your own registered project') from None
        self.ee = ee

    def __call__(self, req, times):
        ee = self.ee
        first = f'{DATASET}/{times[0]:%Y%m%dT%H}'
        asset = retry_transient(lambda: ee.data.getAsset('projects/earthengine-public/assets/'+first))
        validate_native_grid(asset, req.variables)
        image = None
        for stamp in times:
            item = ee.Image(f'{DATASET}/{stamp:%Y%m%dT%H}').select(
                [VARIABLES[v]['band'] for v in req.variables], req.band_names([stamp]))
            image = item if image is None else image.addBands(item)
        raw = retry_transient(lambda: ee.data.computePixels(dict(expression=image, fileFormat='NPY',
            grid=req.grid, bandIds=req.band_names(times), workloadTag='climate-data-access')))
        return decode_response(raw, req, times)
