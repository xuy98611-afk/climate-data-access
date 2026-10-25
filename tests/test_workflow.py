import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from climate_access.config import Request
from climate_access.gee import decode_response, validate_native_grid, retry_transient
from climate_access.artifacts import download, verify_run, bundle


def request(**changes):
    obj = dict(start='2004-01-01T00:00:00Z', end='2004-01-01T02:00:00Z',
               area=[30, 75, 29.5, 75.5], variables=['t2m', 'tp'],
               batch_hours=1, max_output_mib=128)
    obj.update(changes)
    return Request.from_dict(obj)


def synthetic(req, times):
    # Synthetic transport fixture, NOT real ERA5 or physical meteorological values.
    array = np.zeros((req.height, req.width), dtype=[(n, '<f4') for n in req.band_names(times)])
    for number, name in enumerate(array.dtype.names):
        array[name] = np.arange(req.height * req.width).reshape(array.shape) - 2 + number
    return array


class ConfigTests(unittest.TestCase):
    def test_dates_cannot_overflow_netcdf_timestamp_encoding(self):
        with self.assertRaises(ValueError):
            request(start='2500-01-01T00:00:00Z', end='2500-01-01T02:00:00Z')

    def test_extreme_float_bounds_fail_as_validation_errors(self):
        with self.assertRaises(ValueError): request(area=[1e308, 75, 29.5, 75.5])

    def test_native_grid_and_exclusive_end(self):
        req = request()
        self.assertEqual((req.height, req.width, len(req.timestamps)), (3, 3, 2))
        self.assertEqual(req.grid['affineTransform']['translateX'], 74.875)
        self.assertEqual(req.grid['affineTransform']['translateY'], 30.125)
        self.assertEqual(req.band_names(req.timestamps[:1]), ['t2004010100_t2m', 't2004010100_tp'])

    def test_rejects_ambiguous_times_grids_and_private_fields(self):
        invalid = [dict(start='2004-01-01T00:00:00+08:00'), dict(start='2004-01-01T00:30:00Z'),
                   dict(end='2004-01-01T00:00:00Z'), dict(area=[30.1, 75, 29.5, 75.5]),
                   dict(area=[30, 170, 29, -170]), dict(variables=['t2m', 't2m']),
                   dict(variables=['unknown']), dict(batch_hours=True), dict(max_output_mib=float('nan')),
                   dict(start='1939-01-01T00:00:00Z'), dict(token='must-never-be-configured-here'),
                   dict(end='2004-03-01T00:00:00Z')]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                request(**changes)

    def test_bounds_request_memory_before_network(self):
        with self.assertRaises(ValueError):
            request(area=[90, -180, -90, 179.75], batch_hours=24, end='2004-01-02T00:00:00Z')


class TransportTests(unittest.TestCase):
    def test_official_sdk_adapter_offline(self):
        from climate_access.gee import GEEClient
        from climate_access.config import VARIABLES
        req = request(); events = []
        class Image:
            def __init__(self, asset): self.bands=[]; events.append(('image', asset))
            def select(self, source, renamed):
                events.append(('select', source)); self.bands=list(renamed); return self
            def addBands(self, other): self.bands += other.bands; return self
        transform = dict(scaleX=.25, scaleY=-.25, translateX=-180.125, translateY=90.125)
        asset = {'bands':[{'id':VARIABLES[v]['band'], 'grid':{'crsCode':'EPSG:4326',
                         'affineTransform':transform}} for v in req.variables]}
        def pixels(params):
            self.assertEqual(params['expression'].bands, req.band_names(req.timestamps))
            self.assertEqual(params['bandIds'], req.band_names(req.timestamps))
            self.assertEqual(params['grid'], req.grid)
            stream=io.BytesIO(); np.save(stream, synthetic(req, req.timestamps), allow_pickle=False)
            return stream.getvalue()
        fake=SimpleNamespace(Initialize=lambda **kw: events.append(('initialize', kw)), Image=Image,
            data=SimpleNamespace(getAsset=lambda _:asset, computePixels=pixels))
        with patch.dict('sys.modules', {'ee':fake}):
            actual=GEEClient('example-project')(req, req.timestamps)
        np.testing.assert_array_equal(actual, synthetic(req, req.timestamps))
        self.assertEqual(events[0], ('initialize', {'project':'example-project'}))

    def test_rejects_wrong_shape_band_order_and_integer_data(self):
        req=request(); times=req.timestamps[:1]; valid=synthetic(req,times)
        reordered=np.zeros(valid.shape,dtype=[(n,'f4') for n in reversed(valid.dtype.names)])
        for n in reordered.dtype.names:reordered[n]=valid[n]
        bad=[valid[:, :2], reordered,
             np.zeros(valid.shape,dtype=[(n,'i4') for n in valid.dtype.names])]
        for array in bad:
            stream=io.BytesIO();np.save(stream,array,allow_pickle=False)
            with self.assertRaises(ValueError): decode_response(stream.getvalue(),req,times)

    def test_structured_npy_shape_bands_and_values(self):
        req = request(); times = req.timestamps[:1]; a = synthetic(req, times)
        stream = io.BytesIO(); np.save(stream, a, allow_pickle=False)
        np.testing.assert_array_equal(decode_response(stream.getvalue(), req, times), a)
        a[a.dtype.names[0]][0, 0] = np.nan
        stream = io.BytesIO(); np.save(stream, a, allow_pickle=False)
        with self.assertRaises(ValueError):
            decode_response(stream.getvalue(), req, times)
        with self.assertRaises(ValueError):
            decode_response(b'not a response', req, times)

    def test_projection_mismatch_fails(self):
        req = request(); transform = dict(scaleX=.25, scaleY=-.25, shearX=0, shearY=0,
                                         translateX=-180.125, translateY=90.125)
        from climate_access.config import VARIABLES
        asset = {'bands': [{'id': VARIABLES[v]['band'], 'grid': {'crsCode': 'EPSG:4326',
                          'affineTransform': dict(transform)}} for v in req.variables]}
        validate_native_grid(asset, req.variables)
        asset['bands'][0]['grid']['affineTransform']['scaleX'] = .5
        with self.assertRaises(ValueError):
            validate_native_grid(asset, req.variables)

    def test_transient_retry_only_and_sanitized_failure(self):
        class Error(Exception):
            def __init__(self, status):
                self.status_code = status
                super().__init__('provider detail must not be logged')
        calls = []
        def temporary():
            calls.append(1)
            if len(calls) < 3: raise Error(429)
            return 'ok'
        self.assertEqual(retry_transient(temporary, sleep=lambda _: None), 'ok')
        self.assertEqual(len(calls), 3)
        for status in [403, 503]:
            calls.clear()
            def fail():
                calls.append(1); raise Error(status)
            with self.assertRaises(RuntimeError) as result:
                retry_transient(fail, sleep=lambda _: None)
            self.assertNotIn('provider detail', str(result.exception))
            self.assertEqual(len(calls), 1 if status == 403 else 3)


class ArtifactTests(unittest.TestCase):
    def test_budget_rejection_precedes_fetch(self):
        req=request(end='2004-01-02T00:00:00Z',area=[40,89,31,104],
                    variables=['t2m','d2m','sp','tp','ssrd','ssrdc','tcc','u10','v10'],
                    batch_hours=24,max_output_mib=1)
        with tempfile.TemporaryDirectory() as folder:
            def forbidden(*_): self.fail('Budget failure must precede network')
            with self.assertRaises(ValueError): download(req,Path(folder)/'run',forbidden)

    def test_multi_hour_float64_roundtrip(self):
        req=request(batch_hours=2)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run'
            def fetch(r,times):
                a=synthetic(r,times).astype([(n,'f8') for n in r.band_names(times)])
                for n in a.dtype.names:a[n] += .1234567890123
                return a
            expected=fetch(req,req.timestamps)
            download(req,out,fetch)
            import xarray as xr
            with xr.open_dataset(out/'part-00000.nc',engine='h5netcdf') as ds:
                self.assertEqual(ds.t2m.dtype,np.dtype('float64'))
                for i,stamp in enumerate(req.timestamps):
                    np.testing.assert_array_equal(ds.t2m.values[i],expected[f't{stamp:%Y%m%d%H}_t2m'])

    def test_failed_manifest_commit_preserves_uncommitted_file(self):
        import climate_access.artifacts as artifacts
        req=request()
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run'; original=artifacts._manifest; calls=[]
            def interrupted(root,obj):
                calls.append(1)
                if len(calls)==2: raise RuntimeError('offline commit failure')
                return original(root,obj)
            with patch.object(artifacts,'_manifest',interrupted):
                with self.assertRaises(RuntimeError): download(req,out,synthetic)
            raw=(out/'part-00000.nc').read_bytes()
            with self.assertRaises(FileExistsError): download(req,out,synthetic)
            self.assertEqual((out/'part-00000.nc').read_bytes(),raw)
            self.assertFalse((out/'.run.lock').exists())

    def test_existing_writer_lock_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'run'; out.mkdir()
            lock = out/'.run.lock'; lock.write_text('another process')
            with self.assertRaises(FileExistsError): download(request(), out, synthetic)
            self.assertEqual(lock.read_text(), 'another process')

    def test_offline_roundtrip_resume_and_zip(self):
        req = request()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); out = root/'run'; calls = []
            def fetch(r, times):
                self.assertTrue((out/'.run.lock').is_file(), 'A concurrent run must be excluded')
                calls.append(times); return synthetic(r, times)
            download(req, out, fetch)
            summary = verify_run(out)
            self.assertEqual((summary['hours'], summary['files']), (2, 2))
            def forbidden(*args): self.fail('Completed resume called network')
            download(req, out, forbidden)
            self.assertEqual(len(calls), 2)
            import xarray as xr
            with xr.open_dataset(out/'part-00000.nc', engine='h5netcdf') as ds:
                self.assertEqual(ds.t2m.dtype, np.dtype('float32'))
                self.assertEqual(float(ds.tp.values[0, 0, 0]), -1)
                self.assertEqual(ds.attrs['time_standard'], 'UTC')
            archive = root/'delivery.zip'; bundle(out, archive)
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip()); self.assertEqual(len(z.namelist()), 3)
            with self.assertRaises(FileExistsError): bundle(out, archive)
            with self.assertRaises(ValueError): bundle(out, out/'nested.zip')

    def test_failed_batch_resumes_verified_prefix(self):
        req = request()
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'run'; calls = []
            def fail_second(r, times):
                calls.append(times)
                if len(calls) == 2: raise RuntimeError('intentional offline interruption')
                return synthetic(r, times)
            with self.assertRaises(RuntimeError): download(req, out, fail_second)
            with self.assertRaises(ValueError): verify_run(out)
            retried = []
            def finish(r, times):
                retried.append(times); return synthetic(r, times)
            download(req, out, finish)
            self.assertEqual(len(retried), 1); self.assertTrue(verify_run(out)['passed'])

    def test_changed_config_corruption_and_traversal_rejected(self):
        req = request()
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'run'; download(req, out, synthetic)
            with self.assertRaises(ValueError): download(request(variables=['tp']), out, synthetic)
            manifest = out/'manifest.json'; obj = json.loads(manifest.read_text())
            original = manifest.read_bytes()
            obj['files'][0]['name'] = '../outside.nc'; manifest.write_text(json.dumps(obj))
            with self.assertRaises(ValueError): verify_run(out)
            manifest.write_bytes(original)
            with (out/'part-00000.nc').open('ab') as f: f.write(b'corruption')
            with self.assertRaises(ValueError): download(req, out, synthetic)

    def test_unknown_directory_and_nonfinite_response_do_not_publish(self):
        req = request()
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'run'; out.mkdir(); (out/'keep.txt').write_text('user file')
            with self.assertRaises(FileExistsError): download(req, out, synthetic)
            self.assertEqual((out/'keep.txt').read_text(), 'user file')
            out2 = Path(folder)/'other'
            def bad(r, times):
                a = synthetic(r, times); a[a.dtype.names[0]][0, 0] = float('nan'); return a
            with self.assertRaises(ValueError): download(req, out2, bad)
            self.assertFalse(list(out2.glob('*.nc')))


if __name__ == '__main__':
    unittest.main()
