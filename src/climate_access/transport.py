"""Bounded HTTPS for fixed public provider endpoints; no arbitrary URL fetching."""
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def _check_url(url):
    parsed=urlsplit(url)
    paths={'power.larc.nasa.gov': {'/api/temporal/daily/point','/api/temporal/hourly/point'},
           'archive-api.open-meteo.com': {'/v1/archive'}}
    if (parsed.scheme!='https' or parsed.hostname not in paths or parsed.path not in paths.get(parsed.hostname,set())
        or parsed.username is not None or parsed.password is not None or parsed.port not in (None,443) or parsed.fragment):
        raise ValueError('Only fixed HTTPS provider endpoints are allowed')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Provider redirects are not followed')


def http_get(url, *, max_bytes, timeout=60):
    _check_url(url)
    if type(max_bytes) is not int or not 0<max_bytes<=64*1024**2: raise ValueError('Invalid response byte budget')
    if type(timeout) not in (int,float) or not 0<timeout<=120: raise ValueError('Invalid HTTP timeout')
    request=urllib.request.Request(url,headers={'User-Agent':'climate-data-access/0.2','Accept':'application/json'})
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request,timeout=timeout) as response:
            size=response.headers.get('Content-Length')
            if size is not None and int(size)>max_bytes: raise ValueError('Response exceeds byte budget')
            raw=response.read(max_bytes+1)
    except (urllib.error.URLError,TimeoutError,OSError):
        raise RuntimeError('Public provider request failed; check availability and usage limits') from None
    if len(raw)>max_bytes: raise ValueError('Response exceeds byte budget')
    return raw
