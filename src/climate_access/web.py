"""Loopback-only personal workbench; the CLI and page share the same service."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit

from .catalogue import search_sources
from .requests import plan_request, route_capabilities
from .service import fetch_request, verify_request


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False).encode('utf-8')


def _identity(obj):
    return json.dumps(obj, sort_keys=True, allow_nan=False, separators=(',', ':'))


class Workbench:
    def __init__(self, root):
        supplied = Path(root)
        if any(path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())
               for path in (supplied.absolute(), *supplied.absolute().parents)):
            raise ValueError('Output root must not contain symlinks or junctions')
        self.root = supplied.resolve()
        self.token = secrets.token_urlsafe(32)
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='climate-fetch')
        self._future = None
        self._plans = {}
        self._jobs = {}
        if self.root.exists():
            paths = sorted(self.root.glob('run-*/workbench-job.json'))
            ledger = self.root/'.jobs'
            if ledger.is_symlink():
                raise ValueError('Job ledger must not be a symlink')
            paths += sorted(ledger.glob('run-*.json'))
            for path in paths[-1000:]:
                if path.is_symlink() or path.parent.is_symlink() or path.stat().st_size > 65536:
                    continue
                try:
                    job = json.loads(path.read_text(encoding='utf-8'))
                    expected_id = path.stem if path.parent.name == '.jobs' else path.parent.name
                    if (not self.valid_id(job['id']) or job['id'] != expected_id or
                        job['status'] not in {'queued','running','interrupted','complete','failed'} or
                        not isinstance(job.get('request'), dict)):
                        continue
                    if job['status'] in ('queued', 'running'):
                        job.update(status='interrupted', error='上次运行中断；请重新生成计划并执行。')
                    self._jobs[job['id']] = job
                except (OSError, ValueError, KeyError, TypeError):
                    continue

    @staticmethod
    def valid_id(value):
        return isinstance(value, str) and re.fullmatch(r'run-\d{8}T\d{6}-[a-f0-9]{16}', value) is not None

    def jobs(self):
        with self._lock:
            return [dict(job) for job in reversed(list(self._jobs.values()))]

    def plan(self, obj):
        result = plan_request(obj)
        with self._lock:
            now = time.monotonic()
            self._plans = {key: value for key, value in self._plans.items() if now-value[1] < 1800}
            if len(self._plans) >= 100:
                self._plans.pop(next(iter(self._plans)))
            plan_id = secrets.token_urlsafe(24)
            self._plans[plan_id] = (_identity(obj), now)
        return dict(result, plan_id=plan_id)

    def start(self, payload):
        if not isinstance(payload, dict) or set(payload)-{'request', 'plan_id', 'project'}:
            raise ValueError('Expected request, plan_id and optional project')
        obj = payload.get('request')
        plan_request(obj)
        project = payload.get('project')
        if project is not None and (not isinstance(project, str) or not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]', project)):
            raise ValueError('请输入有效的 Earth Engine 项目 ID')
        if obj.get('source', 'era5-gee') == 'era5-gee' and not project:
            raise ValueError('ERA5 获取需要你已获授权的 Earth Engine 项目 ID')
        with self._lock:
            planned = self._plans.get(payload.get('plan_id'))
            if not planned or time.monotonic()-planned[1] >= 1800 or planned[0] != _identity(obj):
                raise ValueError('请先为当前参数生成计划，计划有效期为30分钟')
            if self._future is not None and not self._future.done():
                raise ValueError('已有任务正在获取；请等待完成后再提交')
            self._plans.pop(payload['plan_id'])
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
            job_id = f'run-{stamp}-{secrets.token_hex(8)}'
            job = dict(id=job_id, status='queued', source=obj.get('source', 'era5-gee'),
                       created_utc=datetime.now(timezone.utc).isoformat(), request=obj)
            self._jobs[job_id] = job
            try:
                self._persist(job)
            except (OSError, ValueError):
                self._jobs.pop(job_id)
                raise
            self._future = self._pool.submit(self._execute, job_id, obj, project)
            return dict(job)

    def _persist(self, job):
        ledger = self.root/'.jobs'
        if ledger.is_symlink():
            raise ValueError('Job ledger must not be a symlink')
        ledger.mkdir(parents=True, exist_ok=True)
        target = ledger/(job['id']+'.json')
        temporary = ledger/(job['id']+'.tmp')
        if target.is_symlink() or temporary.is_symlink():
            raise ValueError('Unsafe job record')
        temporary.write_bytes(_json(job))
        temporary.replace(target)

    def _execute(self, job_id, obj, project):
        directory = self.root/job_id
        try:
            with self._lock:
                self._jobs[job_id]['status'] = 'running'
                self._persist(self._jobs[job_id])
            result = fetch_request(obj, directory, project=project)
            if not result.get('passed'):
                raise ValueError('获取结果未通过核验')
            with self._lock:
                self._jobs[job_id].update(status='complete', result=result)
        except Exception as error:
            with self._lock:
                self._jobs[job_id].update(status='failed', error=str(error)[:1500])
        finally:
            with self._lock:
                self._jobs[job_id]['finished_utc'] = datetime.now(timezone.utc).isoformat()
                job = dict(self._jobs[job_id])
            try:
                self._persist(job)
                directory.mkdir(parents=True, exist_ok=True)
                (directory/'workbench-job.json').write_bytes(_json(job))
            except (OSError, ValueError):
                with self._lock:
                    self._jobs[job_id].update(error='任务记录未能写入磁盘；请检查空间和权限')

    def job_directory(self, job_id):
        if not self.valid_id(job_id) or job_id not in self._jobs:
            raise FileNotFoundError('Unknown job')
        target = self.root/job_id
        if target.is_symlink() or target.resolve().parent != self.root:
            raise ValueError('Invalid job directory')
        return target

    def wait_for_idle(self):
        if self._future is not None:
            self._future.result(timeout=180)

    def close(self):
        self._pool.shutdown(wait=True, cancel_futures=False)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_close(self):
        super().server_close()
        self.workbench.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Query parameters and local requests do not enter access logs.

    def _send(self, status, body, content_type='application/json; charset=utf-8', download=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if download:
            self.send_header('Content-Disposition', f'attachment; filename="{download}"')
        self.end_headers()
        self.wfile.write(body)

    def _trusted(self):
        authority = f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host') != authority:
            return False
        origin = self.headers.get('Origin')
        return (not origin or origin == f'http://{authority}') and self.headers.get('Sec-Fetch-Site') != 'cross-site'

    def do_GET(self):
        if not self._trusted():
            return self._send(403, _json({'error':'仅允许本机工作台请求'}))
        wb = self.server.workbench
        path = urlsplit(self.path)
        try:
            if path.path == '/favicon.ico':
                return self._send(204, b'', 'image/x-icon')
            if path.path == '/':
                html = files('climate_access').joinpath('web/index.html').read_text(encoding='utf-8')
                return self._send(200, html.replace('__SESSION_TOKEN__', wb.token).encode(), 'text/html; charset=utf-8')
            if path.path == '/api/catalog':
                query = parse_qs(path.query)
                return self._send(200, _json({'sources':search_sources(query.get('q', [''])[0], tier=query.get('tier', [None])[0] or None)}))
            if path.path == '/api/capabilities':
                return self._send(200, _json({'routes':route_capabilities()}))
            if path.path == '/api/jobs':
                return self._send(200, _json({'jobs':wb.jobs()}))
            parts = path.path.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api', 'jobs'] and parts[3] in {'data.csv','raw.json','manifest.json'}:
                directory = wb.job_directory(parts[2])
                if wb._jobs[parts[2]]['status'] != 'complete':
                    raise ValueError('任务尚未完成')
                target = directory/parts[3]
                if target.is_symlink() or not target.is_file():
                    raise FileNotFoundError('File not available')
                if target.stat().st_size > 32*1024**2:
                    raise ValueError('此文件超过浏览器下载上限，请使用本地输出目录')
                return self._send(200, target.read_bytes(), 'application/octet-stream', target.name)
            return self._send(404, _json({'error':'没有这个页面或结果文件'}))
        except FileNotFoundError:
            self._send(404, _json({'error':'结果文件不存在'}))
        except (ValueError, KeyError, TypeError) as error:
            self._send(400, _json({'error':str(error)}))
        except OSError:
            self._send(500, _json({'error':'无法读取本地结果，请检查磁盘权限'}))

    def do_POST(self):
        wb = self.server.workbench
        if not self._trusted() or not secrets.compare_digest(self.headers.get('X-Workbench-Token', ''), wb.token):
            return self._send(403, _json({'error':'工作台会话无效，请重新打开本地页面'}))
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536 or self.headers.get_content_type() != 'application/json':
                raise ValueError('Expected bounded JSON request')
            self.connection.settimeout(10)
            data = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            if urlsplit(self.path).path == '/api/plan':
                result = wb.plan(data)
            elif urlsplit(self.path).path == '/api/fetch':
                result = wb.start(data)
            elif urlsplit(self.path).path == '/api/verify':
                if not isinstance(data, dict) or set(data) != {'id'}:
                    raise ValueError('Expected a job ID')
                result = verify_request(wb.job_directory(data['id']))
            else:
                return self._send(404, _json({'error':'没有这个操作'}))
            self._send(200, _json(result))
        except (ValueError, KeyError, TypeError, FileNotFoundError) as error:
            self._send(400, _json({'error':str(error)}))
        except (OSError, RuntimeError):
            self._send(500, _json({'error':'操作未完成，请检查本地文件和环境'}))


def make_server(output, port=8765):
    workbench = Workbench(output)
    try:
        server = Server(('127.0.0.1', port), Handler)
    except Exception:
        workbench.close()
        raise
    server.workbench = workbench
    return server


def serve(output='data/workbench', port=8765, open_browser=False):
    server = make_server(output, port)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'气候数据工作台：{url}\n结果目录：{server.workbench.root}\n按 Ctrl+C 停止。', flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
