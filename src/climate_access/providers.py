"""Point-provider request construction and strict interpretation of raw responses."""
import csv
from datetime import datetime, timedelta
from decimal import Decimal
import io
import json
import math
from urllib.parse import urlencode
from .requests import timestamps

POWER_UNITS = {'T2M':{'C'},'T2M_MIN':{'C'},'T2M_MAX':{'C'},'T2MDEW':{'C'},
               'RH2M':{'%'},'WS10M':{'m/s'},'PS':{'kPa'}}
METEO_UNITS = {'temperature_2m':{'°C'},'dew_point_2m':{'°C'},'relative_humidity_2m':{'%'},
               'precipitation':{'mm'},'wind_speed_10m':{'m/s'},'surface_pressure':{'hPa'},'shortwave_radiation':{'W/m²'}}


def provider_url(request):
    times=timestamps(request); point=request['point']
    args=dict(latitude=point['latitude'],longitude=point['longitude'])
    if request['source']=='nasa-power':
        args.update(parameters=','.join(request['variables']),community='AG',
                    start=f'{times[0]:%Y%m%d}',end=f'{times[-1]:%Y%m%d}',format='JSON')
        args['time-standard']='UTC'
        return f"https://power.larc.nasa.gov/api/temporal/{request['frequency']}/point?"+urlencode(args)
    args.update(start_date=f'{times[0]:%Y-%m-%d}',end_date=f'{times[-1]:%Y-%m-%d}',
                hourly=','.join(request['variables']),models='era5',timezone='UTC',elevation='nan',
                cell_selection='nearest',wind_speed_unit='ms')
    return 'https://archive-api.open-meteo.com/v1/archive?'+urlencode(args)


def _unique_pairs(pairs):
    result={}
    for name,value in pairs:
        if name in result: raise ValueError('Duplicate JSON field or timestamp')
        result[name]=value
    return result


def parse_json(raw):
    def invalid(_): raise ValueError('Nonfinite JSON values are not allowed')
    if not isinstance(raw,bytes): raise ValueError('Expected raw JSON bytes')
    try:
        obj=json.loads(raw.decode('utf-8-sig'),parse_float=Decimal,parse_constant=invalid,object_pairs_hook=_unique_pairs)
    except (UnicodeError,json.JSONDecodeError,RecursionError):
        raise ValueError('Invalid JSON provider response') from None
    if not isinstance(obj,dict): raise ValueError('Expected one point JSON object')
    return obj


def _number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float,Decimal)):
        raise ValueError('Expected numeric provider value')
    if isinstance(value,Decimal):
        if not value.is_finite(): raise ValueError('Nonfinite provider value')
    elif not math.isfinite(value): raise ValueError('Nonfinite provider value')
    return value


def _coordinate(latitude,longitude):
    latitude,longitude=float(_number(latitude)),float(_number(longitude))
    if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90<=latitude<=90 or not -180<=longitude<=180:
        raise ValueError('Invalid returned point')
    return dict(latitude=latitude,longitude=longitude)


def _upstream_times(request):
    times=timestamps(request)
    if request['frequency']=='daily': return times
    start=times[0].replace(hour=0)
    end=times[-1].replace(hour=0)+timedelta(days=1)
    return tuple(start+timedelta(hours=i) for i in range((end-start)//timedelta(hours=1)))


def _power(obj,request):
    try:
        header=obj['header']; data=obj['properties']['parameter']; definitions=obj['parameters']
        coordinates=obj['geometry']['coordinates']
        if header['time_standard']!='UTC': raise ValueError('POWER response must explicitly use UTC')
        fill=_number(header['fill_value'])
        if fill!=-999: raise ValueError('Unexpected POWER fill convention')
        sources=header['sources']
        if not isinstance(sources,list) or not sources or any(not isinstance(x,str) or not x for x in sources):
            raise ValueError('Missing POWER source provenance')
        if obj['geometry']['type']!='Point' or not isinstance(coordinates,list) or len(coordinates) not in (2,3):
            raise ValueError('Expected POWER point geometry')
        returned=_coordinate(coordinates[1],coordinates[0])
        if set(data)!=set(request['variables']) or set(definitions)!=set(request['variables']):
            raise ValueError('POWER returned unexpected variables')
        hourly=request['frequency']=='hourly'; pattern='%Y%m%d%H' if hourly else '%Y%m%d'
        expected=[f'{stamp:{pattern}}' for stamp in _upstream_times(request)]
        values={}; units={}
        for variable in request['variables']:
            unit=definitions[variable]['units']
            allowed=POWER_UNITS.get(variable)
            if variable=='PRECTOTCORR': allowed={'mm/hour'} if hourly else {'mm/day'}
            if variable=='ALLSKY_SFC_SW_DWN': allowed={'Wh/m^2'} if hourly else {'kW-hr/m^2/day'}
            if unit not in allowed: raise ValueError('Unexpected POWER units')
            series=data[variable]
            if not isinstance(series,dict) or list(series)!=expected: raise ValueError('POWER UTC sequence is missing, reordered or unexpected')
            values[variable]={}
            for key,value in series.items():
                value=None if value is None else _number(value)
                values[variable][key]=None if value is None or value==fill else value
            units[variable]=unit
        rows=[[f'{stamp:%Y-%m-%d}' if not hourly else f'{stamp:%Y-%m-%dT%H:00:00Z}']+
              [values[v][f'{stamp:{pattern}}'] for v in request['variables']] for stamp in timestamps(request)]
        provenance=dict(provider='NASA POWER',upstream_sources=sources,returned_point=returned,
                        returned_point_meaning='Response location; native grid centers are not supplied per variable',
                        actual_grid_coordinates=None,spatial_method='Original parameter source resolutions; no local interpolation',
                        time_standard='UTC',fill_value=-999,
                        data_nature='Source-derived gridded solar and meteorological data; not a tower observation')
        return rows,units,provenance
    except (KeyError,TypeError,IndexError): raise ValueError('Invalid or incomplete POWER response') from None


def _meteo(obj,request):
    try:
        if type(obj['utc_offset_seconds']) is not int or obj['utc_offset_seconds']!=0:
            raise ValueError('Open-Meteo UTC offset must be zero')
        returned=_coordinate(obj['latitude'],obj['longitude'])
        data=obj['hourly']; definitions=obj['hourly_units']; variables=request['variables']
        if set(data)!=set(variables)|{'time'} or set(definitions)!=set(variables)|{'time'}:
            raise ValueError('Open-Meteo returned unexpected variables')
        if definitions['time']!='iso8601': raise ValueError('Unexpected Open-Meteo time encoding')
        expected=[f'{stamp:%Y-%m-%dT%H:00}' for stamp in _upstream_times(request)]
        if data['time']!=expected: raise ValueError('Open-Meteo UTC sequence is missing, duplicate, reordered or unexpected')
        units={}; values={}
        for variable in variables:
            if definitions[variable] not in METEO_UNITS[variable]: raise ValueError('Unexpected Open-Meteo units')
            if not isinstance(data[variable],list) or len(data[variable])!=len(expected): raise ValueError('Open-Meteo array length mismatch')
            values[variable]=[None if x is None else _number(x) for x in data[variable]]
            units[variable]=definitions[variable]
        index={stamp:i for i,stamp in enumerate(expected)}
        rows=[[f'{stamp:%Y-%m-%dT%H:00:00Z}']+[values[v][index[f'{stamp:%Y-%m-%dT%H:00}']] for v in variables]
              for stamp in timestamps(request)]
        provenance=dict(provider='Open-Meteo historical archive',model='era5',returned_point=returned,
                        actual_grid_coordinates=returned,spatial_method='nearest cell; elevation=nan; no elevation downscaling',
                        time_standard='UTC',wind_speed_unit='m/s',data_nature='ERA5 model data through Open-Meteo processing')
        return rows,units,provenance
    except (KeyError,TypeError,IndexError): raise ValueError('Invalid or incomplete Open-Meteo response') from None


def interpret(raw,request):
    obj=parse_json(raw)
    rows,units,provenance=(_power if request['source']=='nasa-power' else _meteo)(obj,request)
    missing={v:sum(row[i+1] is None for row in rows) for i,v in enumerate(request['variables'])}
    stream=io.StringIO(newline='')
    writer=csv.writer(stream,lineterminator='\n')
    writer.writerow(['time']+request['variables']); writer.writerows(rows)
    return stream.getvalue().encode('utf-8'),dict(units=units,missing_counts=missing,provenance=provenance,record_count=len(rows))
