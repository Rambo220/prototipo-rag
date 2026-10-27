import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import interfaz


class InterfazTests(unittest.TestCase):
    def setUp(self):
        self.server = interfaz.make_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, **extra):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=4)
        headers = {'Content-Type': 'application/json', 'X-Lab-Token': self.server.lab.token}
        headers.update(extra)
        connection.request(method, path, body=None if body is None else json.dumps(body), headers=headers)
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, payload, dict(response.getheaders())

    def test_static_and_restricted_paths(self):
        code, page, headers = self.request('GET', '/')
        self.assertEqual(code, 200)
        self.assertIn('Comparador RAG', page.decode())
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
        self.assertEqual(self.request('GET', '/config.json')[0], 404)
        self.assertEqual(self.request('GET', '/../../rag.py')[0], 404)

    def test_foreign_origin_and_host_are_rejected(self):
        body = {'role': 'Ventas', 'query': 'Consulta'}
        self.assertEqual(self.request('POST', '/api/compare', body, Origin='https://ajeno.example')[0], 403)
        self.assertEqual(self.request('GET', '/', Host='ajeno.example')[0], 403)
        self.assertEqual(self.request('POST', '/api/compare', body, **{'X-Lab-Token': 'incorrecto'})[0], 403)

    def test_invalid_role_blank_and_size(self):
        self.assertEqual(self.request('POST', '/api/compare', {'role': 'Admin', 'query': 'Hola'})[0], 422)
        self.assertEqual(self.request('POST', '/api/compare', {'role': 'Ventas', 'query': '   '})[0], 422)
        self.assertEqual(self.request('POST', '/api/compare', {'role': 'Ventas', 'query': 'a'*8001})[0], 422)

    def test_same_inputs_four_variants_persist_and_download(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            record = {'status': 'ok', 'answer': '<script>texto no ejecutable</script>', 'retrieved': [],
                      'context': [], 'dropped_context': [], 'latency_ms': 1, 'forbidden_retrieved': []}
            with patch('interfaz.prepare', return_value=({}, [], {}, {'signature': 'prueba'}, {})), \
                 patch('interfaz.rag.save_run', return_value=folder), \
                 patch('interfaz.rag.export_csv'), \
                 patch('interfaz.rag.run_case', side_effect=lambda *a, **k: dict(record, variant=a[6])) as run:
                code, data, _ = self.request('POST', '/api/compare', {'role': 'Ventas', 'query': 'Misma consulta'})
                self.assertEqual(code, 202)
                job_id = json.loads(data)['id']
                for _ in range(100):
                    _, raw, _ = self.request('GET', '/api/jobs/'+job_id)
                    job = json.loads(raw)
                    if job['state'] not in ('queued', 'running'):
                        break
                    time.sleep(.01)
                self.assertEqual(job['state'], 'done')
                self.assertEqual([c.args[6] for c in run.call_args_list], ['C0','C1','C2','C3'])
                self.assertTrue(all(c.args[4:6] == ('Misma consulta','Ventas') for c in run.call_args_list))
                self.assertEqual(len((folder/'ejecuciones.jsonl').read_text().splitlines()), 4)
                code, data, headers = self.request('GET', '/api/jobs/'+job_id+'/download')
                self.assertEqual(code, 200)
                self.assertEqual(len(json.loads(data)['results']), 4)
                self.assertIn('attachment', headers['Content-Disposition'])

    def test_busy_and_failures_do_not_become_success(self):
        self.server.lab.gate.acquire()
        try:
            self.assertEqual(self.request('POST', '/api/compare', {'role':'General','query':'Hola'})[0], 409)
        finally:
            self.server.lab.gate.release()
        with patch('interfaz.prepare', side_effect=OSError('No hay motor')):
            _, body, _ = self.request('POST', '/api/compare', {'role':'General','query':'Hola'})
            job_id = json.loads(body)['id']
            for _ in range(100):
                _, body, _ = self.request('GET', '/api/jobs/'+job_id)
                job = json.loads(body)
                if job['state'] == 'error':
                    break
                time.sleep(.01)
            self.assertEqual(job['state'], 'error')
            self.assertEqual(job['results'], [])
            self.assertNotIn('Traceback', job['error'])


if __name__ == '__main__':
    unittest.main()
