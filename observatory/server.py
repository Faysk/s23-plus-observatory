"""API HTTP local-first. Sem operações remotas, upload ou CORS."""
from __future__ import annotations
import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from .collector import Collector, flatten
from .storage import Storage, METRICS, RANGES

ROOT = Path(__file__).resolve().parent.parent
STATIC = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/favicon.svg': 'favicon.svg'}


class State:
    def __init__(self, collector: Collector, storage: Storage, interval: float):
        self.collector, self.storage, self.interval = collector, storage, interval
        self.snapshot = None
        self.updated_at = 0.0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.last_error: str | None = None

    def sample(self):
        data = self.collector.collect()
        epoch = time.time()
        self.storage.record(epoch, flatten(data))
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
                    snap = state.snapshot
                self.respond(200, snap) if snap else self.respond(503, {'error': 'Aguardando primeira amostra'})
                return
            if path == '/api/host/catalog':
                self.respond(200, {'ranges': list(RANGES), 'metrics': {
                    'cpu': {'label': 'CPU', 'unit': '%'},
                    'memory': {'label': 'Memória', 'unit': '%'},
                    'battery': {'label': 'Bateria', 'unit': '%'},
                    'temp': {'label': 'Temperatura da bateria', 'unit': '°C'},
                    'rx': {'label': 'Recebimento', 'unit': 'Mb/s'},
                    'tx': {'label': 'Envio', 'unit': 'Mb/s'},
                    'storage': {'label': 'Armazenamento usado', 'unit': '%'},
                }})
                return
            if path == '/api/host/history':
                query = parse_qs(url.query)
                metric = query.get('metric', ['cpu'])[0]
                period = query.get('range', ['24h'])[0]
                if metric not in METRICS or period not in RANGES:
                    self.respond(400, {'error': 'metric ou range inválido'})
                    return
                self.respond(200, {'metric': metric, 'range': period,
                                   'points': state.storage.history(metric, period)})
                return
            if path in STATIC:
                fp = ROOT / 'web' / STATIC[path]
                if not fp.is_file():
                    self.respond(404, {'error': 'arquivo não encontrado'})
                    return
                mime = mimetypes.guess_type(fp.name)[0] or 'application/octet-stream'
                if mime.startswith('text/') or mime in ('image/svg+xml', 'application/javascript'):
                    mime += '; charset=utf-8'
                self.respond(200, fp.read_bytes(), mime=mime, cache='public, max-age=3600' if path != '/' else 'no-store')
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
