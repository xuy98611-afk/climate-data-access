"""Local HTTP tests never contact upstream data services."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('climate_access.web'), 'Local workbench module is missing')
        from climate_access.web import make_server
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = make_server(Path(self.temp.name)/'outputs', port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def call(self, path, obj=None, **headers):
        data = None if obj is None else json.dumps(obj).encode()
        if obj is not None:
            headers.setdefault('Content-Type', 'application/json')
            headers.setdefault('X-Workbench-Token', self.server.workbench.token)
        with urlopen(Request(self.base+path, data=data, headers=headers), timeout=5) as result:
            return json.load(result)

    def test_page_and_catalogue_are_available_without_network(self):
        with urlopen(self.base) as response:
            page = response.read().decode()
        self.assertIn('气候数据工作台', page)
        self.assertNotIn('__SESSION_TOKEN__', page)
        self.assertIn(self.server.workbench.token, page)
        self.assertEqual(len(self.call('/api/catalog')['sources']), 44)
        self.assertGreater(len(self.call('/api/catalog?q=NASA')['sources']), 0)
        self.assertEqual(self.call('/api/jobs')['jobs'], [])

    def test_plan_does_not_fetch_or_create_output(self):
        obj = dict(source='nasa-power', start='2001-01-01', end='2001-01-03',
                   frequency='daily', point={'latitude':0,'longitude':0}, variables=['T2M'])
        with patch('climate_access.web.fetch_request') as fetch:
            result = self.call('/api/plan', obj)
        fetch.assert_not_called()
        self.assertFalse(result['network_requests_made'])
        self.assertFalse(self.server.workbench.root.exists())

    def test_foreign_host_origin_and_missing_token_are_rejected(self):
        for headers in ({'Host':'evil.example'}, {'Origin':'https://evil.example'}):
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as caught:
                self.call('/api/catalog', **headers)
            self.assertEqual(caught.exception.code, 403)
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.base+'/api/plan', data=b'{}', headers={'Content-Type':'application/json'}))
        self.assertEqual(caught.exception.code, 403)

    def test_invalid_config_and_unknown_paths_return_json(self):
        with self.assertRaises(HTTPError) as caught:
            self.call('/api/plan', {'source':'anything'})
        self.assertEqual(caught.exception.code, 400)
        self.assertIn('error', json.load(caught.exception))
        with self.assertRaises(HTTPError) as caught:
            self.call('/api/jobs/../../private')
        self.assertEqual(caught.exception.code, 404)

    def test_download_requires_a_prior_matching_plan(self):
        with self.assertRaises(HTTPError) as caught:
            self.call('/api/fetch', {'request':{}, 'plan_id':'invented'})
        self.assertEqual(caught.exception.code, 400)

    def test_job_finishes_and_history_survives_restart(self):
        obj = dict(source='nasa-power', start='2001-01-01', end='2001-01-02',
                   frequency='daily', point={'latitude':0,'longitude':0}, variables=['T2M'])
        plan = self.call('/api/plan', obj)
        def local_fetch(request, output, **kwargs):
            Path(output).mkdir(parents=True)
            (Path(output)/'data.csv').write_text('time,T2M\n2001-01-01,25\n')
            return {'passed':True,'rows':1}
        with patch('climate_access.web.fetch_request', side_effect=local_fetch):
            job = self.call('/api/fetch', {'request':obj,'plan_id':plan['plan_id']})
            self.server.workbench.wait_for_idle()
        jobs = self.call('/api/jobs')['jobs']
        self.assertEqual(jobs[0]['id'], job['id'])
        self.assertEqual(jobs[0]['status'], 'complete')
        with urlopen(self.base+f"/api/jobs/{job['id']}/data.csv") as response:
            self.assertIn(b'T2M', response.read())
        from climate_access.web import Workbench
        restored = Workbench(self.server.workbench.root)
        self.addCleanup(restored.close)
        self.assertEqual(restored.jobs()[0]['status'], 'complete')

    def test_running_job_is_persisted_before_download_finishes(self):
        from climate_access.web import Workbench
        obj = dict(source='nasa-power', start='2001-01-01', end='2001-01-02',
                   frequency='daily', point={'latitude':0,'longitude':0}, variables=['T2M'])
        started, release = threading.Event(), threading.Event()
        def blocked_fetch(request, output, **kwargs):
            started.set()
            release.wait(3)
            Path(output).mkdir(parents=True)
            return {'passed':True}
        try:
            with patch('climate_access.web.fetch_request', side_effect=blocked_fetch):
                plan = self.call('/api/plan', obj)
                job = self.call('/api/fetch', {'request':obj,'plan_id':plan['plan_id']})
                self.assertTrue(started.wait(1))
                restored = Workbench(self.server.workbench.root)
                self.addCleanup(restored.close)
                self.assertEqual(len(restored.jobs()), 1)
                self.assertEqual(restored.jobs()[0]['id'], job['id'])
                self.assertEqual(restored.jobs()[0]['status'], 'interrupted')
        finally:
            release.set()
            self.server.workbench.wait_for_idle()

    def test_running_ledger_write_failure_marks_job_failed(self):
        wb = self.server.workbench
        obj = dict(source='nasa-power', start='2001-01-01', end='2001-01-02',
                   frequency='daily', point={'latitude':0,'longitude':0}, variables=['T2M'])
        original = wb._persist
        attempts = []
        def flaky(job):
            attempts.append(job['status'])
            if len(attempts) == 2:
                raise OSError('simulated running ledger failure')
            original(job)
        with patch.object(wb, '_persist', side_effect=flaky), patch('climate_access.web.fetch_request') as fetch:
            plan = wb.plan(obj)
            wb.start({'request':obj, 'plan_id':plan['plan_id']})
            error = None
            try:
                wb.wait_for_idle()
            except OSError as caught:
                error = caught
            self.assertIsNone(error, 'Worker must handle ledger failures')
            fetch.assert_not_called()
            self.assertEqual(wb.jobs()[0]['status'], 'failed')
            self.assertIn('finished_utc', wb.jobs()[0])


if __name__ == '__main__':
    unittest.main()
