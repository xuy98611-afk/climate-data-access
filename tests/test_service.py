"""Offline fixtures test source contracts; these are not meteorological observations."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch


def point(source='nasa-power', **changes):
    obj = dict(source=source, start='2001-01-01', end='2001-01-03', frequency='daily',
               point=dict(latitude=0, longitude=0), variables=['T2M'], max_output_mib=16)
    obj.update(changes)
    return obj


def power(hourly=False):
    values = ({f'20010101{i:02}': i for i in range(24)} if hourly else
              {'20010101': 12.345678901234567, '20010102': -999})
    return dict(type='Feature', geometry=dict(type='Point', coordinates=[0, 0, 1]),
                properties=dict(parameter=dict(T2M=values)),
                header=dict(time_standard='UTC', fill_value=-999, sources=['MERRA2']),
                parameters=dict(T2M=dict(units='C', longname='Temperature')))


def meteo():
    return dict(latitude=0.125, longitude=0.125, utc_offset_seconds=0,
                hourly_units=dict(time='iso8601', temperature_2m='°C'),
                hourly=dict(time=[f'2001-01-01T{i:02}:00' for i in range(24)],
                            temperature_2m=[None]+[i for i in range(1, 24)]))


class UnifiedServiceTests(unittest.TestCase):
    def test_catalog_is_package_resource_and_marks_only_executable_routes(self):
        from climate_access.catalogue import load_catalog, search_sources
        self.assertEqual(len(load_catalog()['sources']), 44)
        self.assertEqual(search_sources('NASA POWER')[0]['executable_routes'], ['nasa-power'])
        self.assertEqual(search_sources('Open-Meteo', tier='no_account')[0]['executable_routes'], ['open-meteo'])
        self.assertTrue(all(x['public_access']['access_tier']=='no_account' for x in search_sources(tier='no_account')))
        self.assertEqual(search_sources('unlikely_unknown_name'), [])

    def test_plans_are_strict_offline_and_end_exclusive(self):
        from climate_access.requests import plan_request
        plan = plan_request(point())
        self.assertEqual(plan['record_count'], 2)
        self.assertFalse(plan['network_requests_made'])
        self.assertTrue(plan['end_is_exclusive'])
        for changes in [dict(token='secret'), dict(source='https://evil.test'), dict(point=dict(latitude=True,longitude=0)),
                        dict(point=dict(latitude=float('nan'),longitude=0)), dict(variables=['T2M','T2M']),
                        dict(variables=['unknown']), dict(max_output_mib=True), dict(max_output_mib=float('inf')),
                        dict(start='1980-01-01'), dict(end='2001-03-01'), dict(end='2001-01-01')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError): plan_request(point(**changes))
        with self.assertRaises(ValueError):
            plan_request(point(frequency='hourly',start='2000-01-01T00:00:00Z',end='2000-01-01T01:00:00Z'))

    def _fetch(self, obj, payload, root):
        from climate_access.service import fetch_request
        calls=[]
        def transport(url, *, max_bytes, timeout):
            calls.append((url,max_bytes,timeout))
            return json.dumps(payload,ensure_ascii=False).encode()
        result=fetch_request(obj,root,transport=transport)
        return result,calls

    def test_power_daily_raw_csv_missing_and_semantic_verification(self):
        from climate_access.service import verify_request
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            result,calls=self._fetch(point(),power(),root)
            self.assertTrue(result['passed'])
            rows=list(csv.DictReader(io.StringIO((root/'data.csv').read_text(encoding='utf-8'))))
            self.assertEqual(rows[1]['T2M'],'')
            self.assertEqual(float(rows[0]['T2M']),12.345678901234567)
            manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['missing_counts'],{'T2M':1})
            self.assertEqual(manifest['provenance']['upstream_sources'],['MERRA2'])
            self.assertTrue(verify_request(root)['passed'])
            self.assertIn('time-standard=UTC',calls[0][0])
            with self.assertRaises(FileExistsError): self._fetch(point(),power(),root)
            # Updating a checksum cannot make a changed CSV semantically valid.
            data=(root/'data.csv').read_bytes().replace(b'12.345678901234567',b'22.345678901234567')
            (root/'data.csv').write_bytes(data)
            for entry in manifest['files']:
                if entry['name']=='data.csv': entry.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaises(ValueError): verify_request(root)

    def test_power_hourly_upstream_day_bounds_and_output_filter(self):
        obj=point(frequency='hourly',start='2001-01-01T02:00:00Z',end='2001-01-01T04:00:00Z')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            _,calls=self._fetch(obj,power(True),root)
            query=parse_qs(urlsplit(calls[0][0]).query)
            self.assertEqual(query['start'],['20010101'])
            self.assertEqual(query['end'],['20010101'])
            rows=list(csv.DictReader(io.StringIO((root/'data.csv').read_text(encoding='utf-8'))))
            self.assertEqual([r['time'] for r in rows],['2001-01-01T02:00:00Z','2001-01-01T03:00:00Z'])

    def test_open_meteo_fixed_model_and_native_grid_metadata(self):
        obj=point('open-meteo',frequency='hourly',start='2001-01-01T00:00:00Z',end='2001-01-01T02:00:00Z',variables=['temperature_2m'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'; _,calls=self._fetch(obj,meteo(),root)
            query=parse_qs(urlsplit(calls[0][0]).query)
            self.assertEqual(query['models'],['era5']); self.assertEqual(query['elevation'],['nan'])
            self.assertEqual(query['wind_speed_unit'],['ms'])
            manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['provenance']['returned_point']['latitude'],0.125)
            self.assertEqual(manifest['missing_counts'],{'temperature_2m':1})

    def test_bad_responses_leave_no_complete_artifact(self):
        from climate_access.service import fetch_request
        invalid=[]
        x=power(); x['header']['time_standard']='LST'; invalid.append(x)
        x=power(); del x['parameters']['T2M']['units']; invalid.append(x)
        x=power(); x['parameters']['T2M']['units']='K'; invalid.append(x)
        x=power(); del x['properties']['parameter']['T2M']['20010102']; invalid.append(x)
        x=power(); x['properties']['parameter']['T2M']['20010101']=float('inf'); invalid.append(x)
        x=power(); x['properties']['parameter']['unexpected']={}; invalid.append(x)
        for payload in invalid:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)/'run'
                with self.assertRaises(ValueError): self._fetch(point(),payload,root)
                self.assertFalse((root/'manifest.json').exists())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            with self.assertRaises(ValueError): fetch_request(point(max_output_mib=1),root,transport=lambda *a,**kw:b'x'*(1024**2+1))
            self.assertFalse(root.exists())

    def test_meteo_wrong_utc_duplicate_time_and_array_shape_rejected(self):
        obj=point('open-meteo',frequency='hourly',start='2001-01-01T00:00:00Z',end='2001-01-01T02:00:00Z',variables=['temperature_2m'])
        for change in ['utc','duplicate','shape']:
            payload=meteo()
            if change=='utc': payload['utc_offset_seconds']=3600
            elif change=='duplicate': payload['hourly']['time'][1]=payload['hourly']['time'][0]
            else: payload['hourly']['temperature_2m'].pop()
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError): self._fetch(obj,payload,Path(tmp)/'run')

    def test_era5_default_delegates_synthetic_transport(self):
        from climate_access.requests import plan_request
        from climate_access.service import fetch_request, verify_request
        import numpy as np
        obj=dict(start='2004-01-01T00:00:00Z',end='2004-01-01T01:00:00Z',area=[0,0,0,0],variables=['t2m'])
        self.assertEqual(plan_request(obj)['source'],'era5-gee')
        def synthetic(req,times): return np.zeros((1,1),dtype=[(name,'<f4') for name in req.band_names(times)])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            self.assertTrue(fetch_request(obj,root,transport=synthetic)['passed'])
            self.assertTrue(verify_request(root)['passed'])

    def test_transport_restricts_remote_hosts_before_network(self):
        from climate_access.transport import http_get
        for url in ['http://power.larc.nasa.gov/api/temporal/daily/point','https://evil.test/x','https://power.larc.nasa.gov@evil.test/x']:
            with self.assertRaises(ValueError): http_get(url,max_bytes=20,timeout=1)

    def test_malformed_field_types_are_validation_errors(self):
        from climate_access.requests import plan_request
        for changes in [dict(source=[]),dict(frequency=[]),dict(point=dict(latitude=10**1000,longitude=0))]:
            with self.subTest(changes=changes),self.assertRaises(ValueError): plan_request(point(**changes))

    def test_transport_stops_at_byte_limit_and_does_not_follow_redirects(self):
        from climate_access.transport import http_get, _NoRedirect
        class Response:
            headers={}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n):
                self.read_size=n
                return b'x'*n
        response=Response()
        class Opener:
            def open(self,request,timeout): return response
        with patch('climate_access.transport.urllib.request.build_opener',return_value=Opener()):
            with self.assertRaises(ValueError): http_get('https://power.larc.nasa.gov/api/temporal/daily/point',max_bytes=8,timeout=1)
        self.assertEqual(response.read_size,9)
        with self.assertRaises(ValueError): _NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test')

    def test_partial_and_manifest_metadata_tampering_are_rejected(self):
        from climate_access.service import verify_request
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'; self._fetch(point(),power(),root)
            manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
            for changes in [dict(status='partial'),dict(missing_counts={'T2M':0}),dict(units={'T2M':'K'}),
                            dict(files=[dict(name='../raw.json',bytes=0,sha256='x')])]:
                (root/'manifest.json').write_text(json.dumps(dict(manifest,**changes)),encoding='utf-8')
                with self.subTest(changes=changes),self.assertRaises(ValueError): verify_request(root)

    def test_duplicate_json_and_long_decimal_values(self):
        from climate_access.service import fetch_request
        with tempfile.TemporaryDirectory() as tmp:
            raw=json.dumps(power()).encode().replace(b'12.345678901234567',b'12.12345678901234567890123456789')
            root=Path(tmp)/'run'
            fetch_request(point(),root,transport=lambda *args,**kwargs:raw)
            self.assertIn(b'12.12345678901234567890123456789',(root/'data.csv').read_bytes())
            duplicate=raw.replace(b'"20010102": -999',b'"20010102": -999, "20010102": 0')
            with self.assertRaises(ValueError): fetch_request(point(),Path(tmp)/'bad',transport=lambda *args,**kwargs:duplicate)

    def test_total_output_budget_counts_raw_csv_and_manifest(self):
        payload=power(); payload['padding']='x'*(1024**2-1000)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            with self.assertRaises(ValueError): self._fetch(point(max_output_mib=1),payload,root)
            self.assertFalse(root.exists())
