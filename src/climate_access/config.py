"""Strict, portable request parameters and native pixel-center geometry."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import math
import re

DATASET = 'ECMWF/ERA5/HOURLY'
VARIABLES = {
    'u10': {'band': 'u_component_of_wind_10m', 'units': 'm s-1'},
    'v10': {'band': 'v_component_of_wind_10m', 'units': 'm s-1'},
    'd2m': {'band': 'dewpoint_temperature_2m', 'units': 'K'},
    't2m': {'band': 'temperature_2m', 'units': 'K'},
    'sp': {'band': 'surface_pressure', 'units': 'Pa'},
    'tp': {'band': 'total_precipitation', 'units': 'm'},
    'ssrdc': {'band': 'surface_solar_radiation_downward_clear_sky', 'units': 'J m-2'},
    'ssrd': {'band': 'surface_solar_radiation_downwards', 'units': 'J m-2'},
    'tcc': {'band': 'total_cloud_cover', 'units': '1'},
}


def _time(text):
    if not isinstance(text, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:00:00Z', text):
        raise ValueError('Use whole UTC hours as YYYY-MM-DDTHH:00:00Z')
    try:
        return datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        raise ValueError('Invalid UTC date') from None


@dataclass(frozen=True)
class Request:
    start: str
    end: str
    area: tuple
    variables: tuple
    batch_hours: int = 6
    max_output_mib: int = 128

    @classmethod
    def from_dict(cls, obj):
        required = {'start', 'end', 'area', 'variables'}
        allowed = required | {'batch_hours', 'max_output_mib'}
        if not isinstance(obj, dict) or set(obj)-allowed or not required <= set(obj):
            raise ValueError('Request has missing or unsupported fields')
        start, end = _time(obj['start']), _time(obj['end'])
        hours = (end-start).total_seconds()/3600
        if start.year < 1940 or not 0 < hours <= 744:
            raise ValueError('Use 1–744 consecutive hours, starting in 1940 or later; split larger runs')
        if end-timedelta(hours=1) > datetime(2262, 4, 11, 23):
            raise ValueError('Requested UTC timestamps exceed the supported NetCDF nanosecond encoding range')
        area = obj['area']
        if not isinstance(area, (list, tuple)) or len(area) != 4:
            raise ValueError('area must be [north, west, south, east]')
        for value in area:
            if type(value) not in (int, float) or not math.isfinite(value) or not -180 <= value <= 180 or not math.isclose(value*4, round(value*4), rel_tol=0, abs_tol=1e-8):
                raise ValueError('Bounds must be finite native 0.25-degree pixel centers')
        north, west, south, east = area
        if not (-90 <= south <= north <= 90 and -180 <= west <= east <= 179.75):
            raise ValueError('Invalid bounds; antimeridian crossing is not supported')
        variables = obj['variables']
        if not isinstance(variables, list) or not variables or any(not isinstance(v, str) or v not in VARIABLES for v in variables) or len(set(variables)) != len(variables):
            raise ValueError('variables must be unique supported short names')
        batch, budget = obj.get('batch_hours', 6), obj.get('max_output_mib', 128)
        if type(batch) is not int or not 1 <= batch <= 24:
            raise ValueError('batch_hours must be an integer from 1 to 24')
        if type(budget) is not int or not 1 <= budget <= 4096:
            raise ValueError('max_output_mib must be an integer from 1 to 4096')
        req = cls(obj['start'], obj['end'], tuple(float(x) for x in area), tuple(variables), batch, budget)
        if req.height*req.width*len(variables)*min(batch, int(hours))*8 > 32*1024**2:
            raise ValueError('Batch exceeds the 32 MiB uncompressed value estimate; reduce region, variables or batch_hours')
        return req

    @property
    def height(self): return round((self.area[0]-self.area[2])*4)+1

    @property
    def width(self): return round((self.area[3]-self.area[1])*4)+1

    @property
    def timestamps(self):
        start, end = _time(self.start), _time(self.end)
        return tuple(start+timedelta(hours=i) for i in range(int((end-start).total_seconds()/3600)))

    @property
    def batches(self):
        times = self.timestamps
        return tuple(times[i:i+self.batch_hours] for i in range(0, len(times), self.batch_hours))

    @property
    def grid(self):
        return {'dimensions': {'width': self.width, 'height': self.height},
                'affineTransform': {'scaleX': .25, 'shearX': 0, 'translateX': self.area[1]-.125,
                                    'shearY': 0, 'scaleY': -.25, 'translateY': self.area[0]+.125},
                'crsCode': 'EPSG:4326'}

    def band_names(self, times):
        return [f't{stamp:%Y%m%d%H}_{variable}' for stamp in times for variable in self.variables]

    def to_dict(self):
        return dict(start=self.start, end=self.end, area=list(self.area), variables=list(self.variables),
                    batch_hours=self.batch_hours, max_output_mib=self.max_output_mib)

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

    def plan(self):
        return dict(dataset=DATASET, request=self.to_dict(), request_sha256=self.fingerprint,
                    grid=self.grid, hours=len(self.timestamps), batches=len(self.batches),
                    decoded_float64_value_bytes=self.height*self.width*len(self.variables)*len(self.timestamps)*8,
                    end_is_exclusive=True, network_requests_made=False,
                    limits_note='Value bytes are an estimate, not total RAM, HTTP traffic or compressed file size')


def load_request(path):
    def invalid(_): raise ValueError('Nonfinite JSON numbers are not allowed')
    with open(path, encoding='utf-8-sig') as stream:
        return Request.from_dict(json.load(stream, parse_constant=invalid))
