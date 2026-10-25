"""Execute explicit requests and independently reparse raw point artifacts on verification."""
import hashlib
import json
from pathlib import Path
from .requests import plan_request
from .providers import provider_url, interpret
from .transport import http_get


def _json_bytes(obj):
    return (json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')


def _fingerprint(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _safe_root(directory):
    root=Path(directory).absolute()
    if any(path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()) for path in (root,*root.parents)):
        raise ValueError('Symlink or junction output paths are not supported')
    return root


def _entry(name,data):
    return dict(name=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def fetch_request(obj,directory,*,project=None,transport=None):
    plan=plan_request(obj); request=plan['request']; root=_safe_root(directory)
    if root.exists(): raise FileExistsError('Use a new output directory; existing files are never overwritten')
    if plan['source']=='era5-gee':
        from .config import Request
        from .gee import GEEClient
        from .artifacts import download
        req=Request.from_dict({k:v for k,v in request.items() if k not in {'source','frequency'}})
        result=download(req,root,transport if transport is not None else GEEClient(project))
        return dict(result,source=plan['source'],directory=str(root),manifest=str(root/'manifest.json'))
    max_bytes=min(request['max_output_mib']*1024**2,64*1024**2)
    raw=(transport or http_get)(provider_url(request),max_bytes=max_bytes,timeout=60)
    if not isinstance(raw,bytes) or len(raw)>max_bytes: raise ValueError('Response exceeds byte budget or is not bytes')
    csv_data,metadata=interpret(raw,request)
    manifest=dict(schema_version=2,status='complete',source=plan['source'],request=request,
                  request_sha256=_fingerprint(request),end_is_exclusive=True,
                  upstream_request_url=provider_url(request),**metadata,
                  processing='Source numeric values; missing values empty in CSV; no imputation or unit conversion',
                  files=[_entry('raw.json',raw),_entry('data.csv',csv_data)])
    manifest_data=_json_bytes(manifest)
    if len(raw)+len(csv_data)+len(manifest_data)>request['max_output_mib']*1024**2:
        raise ValueError('Artifacts exceed configured output budget')
    root.mkdir(parents=True,exist_ok=False)
    # The complete manifest is published last. Any interrupted directory is visibly incomplete.
    for name,data in [('raw.json',raw),('data.csv',csv_data),('manifest.json',manifest_data)]:
        with (root/name).open('xb') as stream: stream.write(data)
    return dict(verify_request(root),directory=str(root),manifest=str(root/'manifest.json'),
                csv=str(root/'data.csv'),raw=str(root/'raw.json'))


def verify_request(directory):
    root=_safe_root(directory); path=root/'manifest.json'
    if path.is_symlink() or not path.is_file(): raise ValueError('Missing or unsafe manifest')
    if path.stat().st_size>1024**2: raise ValueError('Manifest exceeds byte budget')
    try: manifest=json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,UnicodeError): raise ValueError('Invalid manifest JSON') from None
    if not isinstance(manifest,dict): raise ValueError('Invalid manifest')
    if manifest.get('schema_version')==1 and manifest.get('source_dataset')=='ECMWF/ERA5/HOURLY':
        from .artifacts import verify_run
        return dict(verify_run(root),source='era5-gee')
    if manifest.get('schema_version')!=2 or manifest.get('status')!='complete': raise ValueError('Run is incomplete or schema unsupported')
    try:
        plan=plan_request(manifest['request']); request=plan['request']
        if (manifest['source']!=request['source'] or request['source']=='era5-gee' or
            request!=manifest['request'] or manifest['request_sha256']!=_fingerprint(request) or
            manifest.get('end_is_exclusive') is not True or manifest.get('upstream_request_url')!=provider_url(request)):
            raise ValueError('Manifest request identity mismatch')
        entries=manifest['files']
        if not isinstance(entries,list) or [e['name'] for e in entries]!=['raw.json','data.csv']:
            raise ValueError('Unexpected artifact filenames')
        budget=request['max_output_mib']*1024**2; total=path.stat().st_size; artifacts={}
        for entry in entries:
            artifact=root/entry['name']
            if artifact.is_symlink() or not artifact.is_file() or artifact.resolve().parent!=root.resolve():
                raise ValueError('Missing or unsafe artifact')
            size=artifact.stat().st_size; total+=size
            if size>64*1024**2 or total>budget: raise ValueError('Artifacts exceed output budget')
            data=artifact.read_bytes()
            if _entry(entry['name'],data)!=entry: raise ValueError('Artifact checksum mismatch')
            artifacts[entry['name']]=data
        expected,metadata=interpret(artifacts['raw.json'],request)
        if expected!=artifacts['data.csv']: raise ValueError('CSV does not match the original response')
        if any(manifest.get(name)!=value for name,value in metadata.items()):
            raise ValueError('Manifest metadata does not match original response')
    except (KeyError,TypeError): raise ValueError('Incomplete or invalid manifest') from None
    return dict(passed=True,source=request['source'],record_count=metadata['record_count'],
                missing_counts=metadata['missing_counts'],request_sha256=manifest['request_sha256'],
                checks=['SHA256','raw response reparse','exact CSV correspondence','UTC sequence','variables','units','missing counts','provenance','output budget'],
                limitation='Consistency and provenance checks; not independent meteorological accuracy validation')
