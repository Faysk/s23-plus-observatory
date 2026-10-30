#!/usr/bin/env python3
import argparse
from pathlib import Path
from observatory.collector import Collector
from observatory.storage import Storage
from observatory.server import State, serve


def parse_args():
    parser = argparse.ArgumentParser(description='Galaxy S23+ Observatory (somente leitura)')
    parser.add_argument('--bind', default='127.0.0.1', help='default: 127.0.0.1')
    parser.add_argument('--port', type=int, default=8783)
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--db', default=str(Path.home() / '.local/share/s23-observatory/metrics.sqlite3'))
    parser.add_argument('--retention', type=int, default=90, help='dias, 1..3650')
    parser.add_argument('--unsafe-lan', action='store_true', help='exposição LAN sem autenticação, não recomendado')
    args = parser.parse_args()
    if args.interval < 10 or args.interval > 3600:
        parser.error('--interval deve ser de 10 a 3600 segundos')
    if not 1 <= args.port <= 65535:
        parser.error('--port inválida')
    if args.bind not in ('127.0.0.1', '::1', 'localhost') and not args.unsafe_lan:
        parser.error('bind público bloqueado por segurança; use túnel SSH ou --unsafe-lan conscientemente')
    return args


def main():
    args = parse_args()
    storage = Storage(args.db, args.retention)
    state = State(Collector(), storage, args.interval)
    serve(args.bind, args.port, state)


if __name__ == '__main__':
    main()
