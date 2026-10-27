"""Comparador local. Reutiliza rag.py sin cambiar el experimento.

Servidor de laboratorio: https://docs.python.org/3/library/http.server.html
"""
import copy
import hashlib
import json
import logging
import re
import secrets
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import rag

ROOT = Path(__file__).resolve().parent
APP_ID = 'taller-rag-comparador-1'


def prepare():
    cfg, docs = rag.config(), rag.corpus()
    identity = rag.models(cfg)
    index = rag.load_index(cfg, docs, identity)
    meta = rag.snapshot(cfg, docs, identity)
    meta['interface_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return cfg, docs, identity, index, meta


def user_error(exc):
    if isinstance(exc, ValueError):
        return str(exc)
    return 'No se pudo completar la operación. Comprobá que el motor local esté iniciado y revisá la guía del proyecto.'


class Lab:
    def __init__(self):
        self.token = secrets.token_urlsafe(32)
        self.gate = threading.Lock()
        self.mutex = threading.Lock()
        self.jobs = {}
        self.latest = None

    def get(self, job_id):
        with self.mutex:
            return copy.deepcopy(self.jobs.get(job_id))

    def change(self, job_id, **fields):
        with self.mutex:
            self.jobs[job_id].update(fields)

    def start(self, role, query):
        if not self.gate.acquire(blocking=False):
            return None
        job_id = uuid.uuid4().hex
        with self.mutex:
            # Resultados completos permanecen en disco. La memoria conserva las últimas diez comparaciones.
            if len(self.jobs) >= 10:
                self.jobs.pop(next(iter(self.jobs)))
            self.jobs[job_id] = {'id': job_id, 'role': role, 'query': query, 'state': 'queued',
                                 'current': None, 'results': [], 'error': None, 'evidence': None}
            self.latest = job_id
        try:
            threading.Thread(target=self.run, args=(job_id,), daemon=True).start()
        except Exception:
            self.gate.release()
            raise
        return job_id

    def run(self, job_id):
        folder, records = None, []
        try:
            job = self.get(job_id)
            self.change(job_id, state='running')
            cfg, docs, identity, index, meta = prepare()
            meta.update(query=job['query'], role=job['role'], variants=list(rag.VARIANTS),
                        execution_order='C0,C1,C2,C3 sequential', interface='web-local')
            folder = rag.save_run(meta, [], 'technical-ui')
            self.change(job_id, evidence='resultados/'+folder.name)
            with (folder/'ejecuciones.jsonl').open('a', encoding='utf-8') as stream:
                for variant in rag.VARIANTS:
                    self.change(job_id, current=variant)
                    record = rag.run_case(cfg, docs, identity, index, job['query'], job['role'],
                                          variant, case_id='ui-'+job_id, repetition=1)
                    records.append(record)
                    stream.write(json.dumps(record, ensure_ascii=False)+'\n')
                    stream.flush()
                    rag.export_csv(folder, records)
                    self.change(job_id, results=copy.deepcopy(records))
            # Detectar edición de archivos o cambio de modelos mientras la comparación estaba en curso.
            after = prepare()
            same = (cfg == after[0] and rag.digest(docs) == rag.digest(after[1]) and identity == after[2])
            if not same:
                raise ValueError('El entorno cambió durante la comparación. No mezcles estos resultados; repetí con una versión fija.')
            state = 'done' if all(r['status'] == 'ok' for r in records) else 'partial'
            self.change(job_id, state=state, current=None)
        except Exception as exc:
            logging.exception('Error en comparación %s', job_id)
            self.change(job_id, state='error', error=user_error(exc), current=None)
        finally:
            try:
                if folder is not None:
                    rag.write_json(folder/'comparacion.json', self.get(job_id))
                    rag.export_csv(folder, records)
            except Exception as exc:
                logging.exception('No se pudo guardar la comparación %s', job_id)
                self.change(job_id, state='error', error='No se pudo guardar toda la evidencia. Revisá el espacio disponible y repetí la comparación.')
            self.gate.release()


class Handler(BaseHTTPRequestHandler):
    server_version = 'LaboratorioRAG'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, fmt, *args):
        logging.info('%s %s', self.client_address[0], fmt % args)

    def allowed_request(self, mutate=False):
        hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in hosts:
            self.send_json(403, {'error': 'Acceso permitido únicamente desde esta PC.'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in {'http://'+h for h in hosts}:
            self.send_json(403, {'error': 'Origen no permitido.'})
            return False
        if mutate and not secrets.compare_digest(self.headers.get('X-Lab-Token', ''), self.server.lab.token):
            self.send_json(403, {'error': 'Recargá esta página antes de continuar.'})
            return False
        return True

    def send_bytes(self, status, payload, mime, filename=None):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, status, data, filename=None):
        self.send_bytes(status, json.dumps(data, ensure_ascii=False).encode(), 'application/json; charset=utf-8', filename)

    def do_GET(self):
        if not self.allowed_request():
            return
        path = urlsplit(self.path).path
        static = {'/': ('index.html', 'text/html'), '/app.css': ('app.css','text/css'),
                  '/app.js': ('app.js','text/javascript')}
        if path in static:
            name, mime = static[path]
            self.send_bytes(200, (ROOT/'web'/name).read_bytes(), mime+'; charset=utf-8')
        elif path == '/favicon.ico':
            self.send_bytes(204, b'', 'image/x-icon')
        elif path == '/api/status':
            state = {'application': APP_ID, 'token': self.server.lab.token, 'ready': False,
                     'latest': self.server.lab.latest, 'roles': list(rag.ROLES)}
            try:
                cfg, docs, identity, index, meta = prepare()
                state.update(ready=True, model=cfg['chat_model'], embeddings=cfg['embedding_model'],
                             documents=len(docs), error=None)
            except Exception as exc:
                state['error'] = user_error(exc)
            self.send_json(200, state)
        else:
            match = re.fullmatch(r'/api/jobs/([a-f0-9]{32})(/download)?', path)
            job = self.server.lab.get(match[1]) if match else None
            if job is None:
                self.send_json(404, {'error':'No se encontró ese recurso.'})
            else:
                self.send_json(200, job, 'comparacion-rag-'+job['id'][:8]+'.json' if match[2] else None)

    def do_POST(self):
        if not self.allowed_request(mutate=True):
            return
        if self.path != '/api/compare':
            self.send_json(404, {'error':'No se encontró ese recurso.'})
            return
        if self.headers.get('Content-Type','').split(';')[0].strip() != 'application/json':
            self.send_json(415, {'error':'Formato de solicitud no admitido.'})
            return
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 40000:
                self.send_json(413, {'error':'La consulta supera el tamaño admitido.'})
                return
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict) or set(data) != {'role','query'}:
                raise ValueError('Elegí un rol y escribí una consulta.')
            role, query = data['role'], data['query']
            if role not in rag.ROLES or not isinstance(query, str) or not 0 < len(query.strip()) <= 8000:
                raise ValueError('Elegí un rol válido y escribí entre 1 y 8000 caracteres.')
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(422, {'error':'Elegí un rol válido y escribí una consulta de hasta 8000 caracteres.'})
            return
        job_id = self.server.lab.start(role, query.strip())
        if job_id is None:
            self.send_json(409, {'error':'Hay una comparación en curso. Esperá a que termine.'})
        else:
            self.send_json(202, {'id': job_id})


def make_server(port=8765):
    # BaseHTTPRequestHandler + ThreadingHTTPServer se usan solo como servidor local de laboratorio.
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.lab = Lab()
    return server


def main():
    runtime = ROOT/'.runtime'
    runtime.mkdir(exist_ok=True)
    logging.basicConfig(filename=runtime/'interfaz.log', level=logging.INFO, encoding='utf-8')
    server = make_server()
    (runtime/'interfaz.pid').write_text(str(__import__('os').getpid()), encoding='ascii')
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
