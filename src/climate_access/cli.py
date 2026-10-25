import argparse
import json
from .config import load_request


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explicit native-grid ERA5 retrieval and verification')
    parser.add_argument('--version', action='version', version='0.1.0')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('plan', help='Validate and estimate offline').add_argument('config')
    fetch = sub.add_parser('fetch', help='Explicitly request GEE using your own authentication')
    fetch.add_argument('config'); fetch.add_argument('--project', required=True); fetch.add_argument('--output', required=True)
    sub.add_parser('verify', help='Verify a complete local run').add_argument('directory')
    pack = sub.add_parser('bundle', help='Verify and create a ZIP without overwriting')
    pack.add_argument('directory'); pack.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'plan':
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
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'passed':False,'error':str(error)}, ensure_ascii=False))
        return 1
