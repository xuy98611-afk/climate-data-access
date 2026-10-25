import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from climate_access.cli import main


class UnifiedCLITests(unittest.TestCase):
    def run_cli(self, args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = main(args)
        return code, json.loads(stream.getvalue())

    def test_catalog_is_available_from_any_working_directory(self):
        code, obj = self.run_cli(['catalog', '--search', 'NASA'])
        self.assertEqual(code, 0)
        self.assertGreater(obj['source_count'], 0)

    def test_point_plan_and_invalid_source(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'request.json'
            obj = dict(source='nasa-power', start='2001-01-01', end='2001-01-03',
                       frequency='daily', point={'latitude':0,'longitude':0}, variables=['T2M'])
            config.write_text(json.dumps(obj), encoding='utf-8')
            code, result = self.run_cli(['request-plan', str(config)])
            self.assertEqual(code, 0)
            self.assertEqual(result['record_count'], 2)
            self.assertFalse(result['network_requests_made'])
            obj['source'] = 'unknown'
            config.write_text(json.dumps(obj), encoding='utf-8')
            code, result = self.run_cli(['request-plan', str(config)])
            self.assertEqual(code, 1)
            self.assertFalse(result['passed'])
