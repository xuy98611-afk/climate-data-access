"""Strict offline request planning with explicit provider and time semantics."""
from datetime import datetime, timedelta, timezone
import math
import re
from .config import Request, VARIABLES, _time

POWER_VARIABLES = {'T2M': '气温', 'T2M_MIN': '最低气温', 'T2M_MAX': '最高气温',
                   'T2MDEW': '露点', 'RH2M': '相对湿度', 'PRECTOTCORR': '降水',
                   'WS10M': '10米风速', 'PS': '气压', 'ALLSKY_SFC_SW_DWN': '短波辐射'}
METEO_VARIABLES = {'temperature_2m': '气温', 'relative_humidity_2m': '相对湿度',
                   'dew_point_2m': '露点', 'precipitation': '降水', 'wind_speed_10m': '10米风速',
                   'surface_pressure': '地表气压', 'shortwave_radiation': '短波辐射'}


def route_capabilities():
    return [dict(source=source, label=label, kind=kind, frequencies=freq,
                 variables=[dict(code=code, label=name) for code, name in variables.items()], auth=auth)
            for source, label, kind, freq, variables, auth in [
                ('era5-gee','ERA5 / Google Earth Engine','area',['hourly'],{v:v for v in VARIABLES},'User-owned registered GEE project and authentication'),
                ('nasa-power','NASA POWER','point',['daily','hourly'],POWER_VARIABLES,'No account; public API limits apply'),
                ('open-meteo','Open-Meteo / ERA5','point',['hourly'],METEO_VARIABLES,'No account; public noncommercial API terms apply')]]


def _daily(text):
    if not isinstance(text,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',text):
        raise ValueError('Daily dates must use YYYY-MM-DD')
    try: return datetime.strptime(text,'%Y-%m-%d')
    except ValueError: raise ValueError('Invalid daily date') from None


def timestamps(request):
    daily = request['frequency']=='daily'
    start = _daily(request['start']) if daily else _time(request['start'])
    end = _daily(request['end']) if daily else _time(request['end'])
    step = timedelta(days=1) if daily else timedelta(hours=1)
    return tuple(start+i*step for i in range((end-start)//step))


def plan_request(obj):
    if not isinstance(obj,dict): raise ValueError('Request must be a JSON object')
    source = obj.get('source','era5-gee')
    if not isinstance(source,str): raise ValueError('source must be an executable route string')
    if source=='era5-gee':
        if obj.get('frequency','hourly')!='hourly': raise ValueError('ERA5 requires hourly frequency')
        req=Request.from_dict({k:v for k,v in obj.items() if k not in {'source','frequency'}})
        return dict(req.plan(), source=source, variables=list(req.variables), record_count=len(req.timestamps),
                    request=dict(req.to_dict(),source=source,frequency='hourly'),
                    authentication_required=True, auth_requirements='Registered user-owned GEE project and local authentication',
                    time_standard='UTC', spatial_method='Native 0.25 degree pixel centers; no interpolation')
    if source not in {'nasa-power','open-meteo'}: raise ValueError('Unknown executable source')
    required={'source','start','end','frequency','point','variables'}
    if not required<=set(obj) or set(obj)-required-{'max_output_mib'}:
        raise ValueError('Request has missing or unsupported fields')
    frequency=obj['frequency']
    if not isinstance(frequency,str) or frequency not in ({'daily','hourly'} if source=='nasa-power' else {'hourly'}):
        raise ValueError('Unsupported source frequency')
    start = _daily(obj['start']) if frequency=='daily' else _time(obj['start'])
    end = _daily(obj['end']) if frequency=='daily' else _time(obj['end'])
    minimum=datetime(1981 if source=='nasa-power' and frequency=='daily' else 2001 if source=='nasa-power' else 1940,1,1)
    if start<minimum or not timedelta(0)<end-start<=timedelta(days=31):
        raise ValueError('Use a covered interval of at most 31 days')
    if end>datetime.now(timezone.utc).replace(tzinfo=None): raise ValueError('Historical requests cannot include future timestamps')
    point=obj['point']
    if not isinstance(point,dict) or set(point)!={'latitude','longitude'}:
        raise ValueError('point must contain only latitude and longitude')
    for name,limit in [('latitude',90),('longitude',180)]:
        value=point[name]
        if type(value) not in (int,float) or not -limit<=value<=limit or not math.isfinite(value):
            raise ValueError('Point coordinates must be finite geographic numbers')
    variables=obj['variables']; allowed=POWER_VARIABLES if source=='nasa-power' else METEO_VARIABLES
    if (not isinstance(variables,list) or not 1<=len(variables)<=8 or
        any(not isinstance(v,str) or v not in allowed for v in variables) or len(set(variables))!=len(variables)):
        raise ValueError('Use 1–8 unique supported variables')
    if frequency=='hourly' and set(variables)&{'T2M_MIN','T2M_MAX'}:
        raise ValueError('POWER minimum and maximum variables are daily only')
    budget=obj.get('max_output_mib',16)
    if type(budget) is not int or not 1<=budget<=4096: raise ValueError('max_output_mib must be an integer from 1 to 4096')
    canonical=dict(source=source,start=obj['start'],end=obj['end'],frequency=frequency,
                   point={k:float(v) for k,v in point.items()},variables=list(variables),max_output_mib=budget)
    return dict(source=source,request=canonical,variables=list(variables),record_count=len(timestamps(canonical)),
                hours=len(timestamps(canonical)) if frequency=='hourly' else None,
                end_is_exclusive=True,network_requests_made=False,authentication_required=False,
                auth_requirements='No account; check upstream public API usage terms',time_standard='UTC',
                spatial_method=('Source-native parameter grids; returned geometry is not proof of grid center' if source=='nasa-power' else
                                'ERA5 model; nearest cell; elevation downscaling disabled'),
                limits_note='31 day and 8 variable local safety bounds; upstream availability must still be checked')
