"""API HTTP local-first. Sem operações remotas, upload ou CORS."""
from __future__ import annotations
import copy
import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from .collector import Collector, flatten
from .storage import Storage, METRICS, RANGES
from .catalog import catalog

ROOT = Path(__file__).resolve().parent.parent
STATIC = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/favicon.svg': 'favicon.svg', '/charts.js': 'charts.js'}


class State:
    def __init__(self, collector: Collector, storage: Storage, interval: float):
        self.collector, self.storage, self.interval = collector, storage, interval
        self.snapshot = None
        self.failures = 0
        self.updated_at = 0.0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.last_error: str | None = None

    def sample(self):
        data = self.collector.collect()
        epoch = time.time()
        data.setdefault('diagnostics', {})['sampleIntervalSec'] = self.interval
        self.storage.record(epoch, flatten(data), data)
        with self.lock:
            self.snapshot, self.updated_at, self.last_error = data, epoch, None

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.sample()
            except Exception as ex:
                # Não imprimir detalhes do host ou variáveis de ambiente.
                with self.lock:
                    self.last_error = type(ex).__name__
                    self.failures += 1
            self.stop_event.wait(self.interval)

    def start(self):
        self.thread = threading.Thread(target=self.run, name='collector', daemon=True)
        self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.storage.close()


def handler_factory(state: State):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'S23Observatory/0.1'
        sys_version = ''

        def respond(self, code, payload, mime='application/json; charset=utf-8', cache='no-store'):
            body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', cache)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            path = url.path
            if path in ('/', '/s23'):
                self.send_response(302)
                self.send_header('Location', '/s23/')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if not path.startswith('/s23/'):
                self.respond(404, {'error': 'rota não encontrada'})
                return
            path = path[len('/s23'):]
            if path == '/api/health':
                with state.lock:
                    last = state.updated_at
                    err = state.last_error
                self.respond(200 if last and time.time() - last < max(60, 3 * state.interval) else 503,
                             {'ok': bool(last and time.time() - last < max(60, 3 * state.interval)),
                              'lastSample': last or None, 'lastErrorType': err})
                return
            if path == '/api/host/snapshot':
                with state.lock:
                    snap = copy.deepcopy(state.snapshot)
                    updated = state.updated_at
                    last_error = state.last_error
                if snap:
                    snap['ageSeconds'] = round(max(0, time.time()-updated),1)
                    snap['quality'] = 'stale' if time.time()-updated > max(60, state.interval*2.5) else 'ok'
                    snap.setdefault('diagnostics', {})['lastError'] = last_error
                self.respond(200, snap) if snap else self.respond(503, {'error': 'Aguardando primeira amostra'})
                return
            if path == '/api/host/catalog':
                with state.lock:
                    snap = state.snapshot
                self.respond(200, {'ranges': list(RANGES), 'metrics': catalog(snap),
                                   'sampleIntervalSec': state.interval, 'storage': state.storage.info()})
                return
            if path == '/api/host/archive':
                query = parse_qs(url.query)
                try:
                    data = state.storage.archive(int(query.get('after', ['0'])[0]), int(query.get('limit', ['50'])[0]))
                except ValueError:
                    self.respond(400, {'error': 'cursor ou limite inválido'})
                    return
                self.respond(200, data)
                return
            if path == '/api/host/history':
                query = parse_qs(url.query)
                metric = query.get('metric', ['cpu'])[0]
                period = query.get('range', ['24h'])[0]
                if metric not in METRICS or period not in RANGES:
                    self.respond(400, {'error': 'metric ou range inválido'})
                    return
                self.respond(200, {'metric': metric, 'range': period,
                                   'points': state.storage.history(metric, period),
                                   'summary': state.storage.summary(metric, period),
                                   'sampleIntervalSec': state.interval})
                return
            if path in STATIC:
                fp = ROOT / 'web' / STATIC[path]
                if not fp.is_file():
                    self.respond(404, {'error': 'arquivo não encontrado'})
                    return
                mime = mimetypes.guess_type(fp.name)[0] or 'application/octet-stream'
                if mime.startswith('text/') or mime in ('image/svg+xml', 'application/javascript'):
                    mime += '; charset=utf-8'
                self.respond(200, fp.read_bytes(), mime=mime, cache='no-cache' if path != '/' else 'no-store')
                return
            self.respond(404, {'error': 'rota não encontrada'})

        def do_POST(self):
            self.respond(405, {'error': 'Somente leitura'})

        def log_message(self, format, *args):
            # Não registrar IP dos clientes por padrão.
            pass

    return Handler


def serve(host: str, port: int, state: State):
    server = ThreadingHTTPServer((host, port), handler_factory(state))
    print(f'S23 Observatory: http://{host}:{server.server_port} (Ctrl+C para parar)', flush=True)
    state.start()
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        state.close()
