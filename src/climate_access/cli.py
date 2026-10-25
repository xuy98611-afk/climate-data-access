import argparse
import json
from .config import load_request
from . import __version__


def _load_json(path):
    def invalid(_):
        raise ValueError('Nonfinite JSON numbers are not allowed')
    with open(path, encoding='utf-8-sig') as stream:
        return json.load(stream, parse_constant=invalid)


def main(argv=None):
    parser = argparse.ArgumentParser(description='统一气候数据入口：目录、计划、显式获取与核验')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('plan', help='Validate and estimate offline').add_argument('config')
    fetch = sub.add_parser('fetch', help='Explicitly request GEE using your own authentication')
    fetch.add_argument('config'); fetch.add_argument('--project', required=True); fetch.add_argument('--output', required=True)
    sub.add_parser('verify', help='Verify a complete local run').add_argument('directory')
    pack = sub.add_parser('bundle', help='Verify and create a ZIP without overwriting')
    pack.add_argument('directory'); pack.add_argument('--output', required=True)
    catalog = sub.add_parser('catalog', help='检索随包发布的44项渠道目录')
    catalog.add_argument('--search', default=''); catalog.add_argument('--tier')
    sub.add_parser('request-plan', help='验证统一请求并离线生成计划').add_argument('config')
    unified = sub.add_parser('request-fetch', help='执行显式来源的统一请求')
    unified.add_argument('config'); unified.add_argument('--output', required=True); unified.add_argument('--project')
    sub.add_parser('request-verify', help='从原始响应回读核验统一结果').add_argument('directory')
    web = sub.add_parser('serve', help='启动本机中文工作台')
    web.add_argument('--output', default='data/workbench'); web.add_argument('--port', type=int, default=8765)
    web.add_argument('--open', action='store_true', dest='open_browser')
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            from .web import serve
            if not 0 <= args.port <= 65535:
                raise ValueError('Port must be between 0 and 65535')
            serve(args.output, args.port, args.open_browser)
            return 0
        if args.command == 'catalog':
            from .catalogue import search_sources
            sources = search_sources(args.search, args.tier)
            result = {'source_count':len(sources), 'sources':sources}
        elif args.command == 'request-plan':
            from .requests import plan_request
            result = plan_request(_load_json(args.config))
        elif args.command == 'request-fetch':
            from .service import fetch_request
            request = _load_json(args.config)
            if request.get('source', 'era5-gee') == 'era5-gee' and not args.project:
                raise ValueError('ERA5 GEE requires --project with your own authorized project')
            result = fetch_request(request, args.output, project=args.project)
        elif args.command == 'request-verify':
            from .service import verify_request
            result = verify_request(args.directory)
        elif args.command == 'plan':
            result = load_request(args.config).plan()
        else:
            from .artifacts import download, verify_run, bundle
            if args.command == 'verify': result = verify_run(args.directory)
            elif args.command == 'bundle': result = bundle(args.directory, args.output)
            else:
                from .gee import GEEClient
                client = None
                def remote(req, times):
                    nonlocal client
                    if client is None: client = GEEClient(args.project)
                    return client(req, times)
                result = download(load_request(args.config), args.output, remote)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, ImportError, AttributeError) as error:
        print(json.dumps({'passed':False,'error':str(error)}, ensure_ascii=False))
        return 1
