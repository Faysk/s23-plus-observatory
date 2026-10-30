"""Histórico SQLite com retenção explícita e buckets sem interpolação."""
from __future__ import annotations
import datetime as dt
import sqlite3
import threading
import time
from pathlib import Path

RANGES = {'1h': 3600, '6h': 21600, '12h': 43200, '24h': 86400,
          '7d': 604800, '30d': 2592000, '90d': 7776000}
METRICS = {'cpu', 'memory', 'battery', 'temp', 'rx', 'tx', 'storage'}


class Storage:
    def __init__(self, path: str, retention_days: int = 90):
        if not 1 <= retention_days <= 3650:
            raise ValueError('retention_days deve ficar entre 1 e 3650')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=5)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA busy_timeout=5000')
        self.conn.execute('CREATE TABLE IF NOT EXISTS samples '
                          '(ts REAL NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL, '
                          'PRIMARY KEY(ts, metric))')
        self.conn.execute('CREATE INDEX IF NOT EXISTS samples_metric_ts ON samples(metric, ts)')
        self.conn.commit()
        self.lock = threading.Lock()
        self.retention_days = retention_days
        self.last_cleanup = 0.0

    def record(self, epoch: float, values: dict[str, float]):
        rows = [(epoch, name, value) for name, value in values.items() if name in METRICS]
        with self.lock:
            if rows:
                self.conn.executemany('INSERT OR REPLACE INTO samples(ts, metric, value) VALUES (?, ?, ?)', rows)
            # Apaga somente uma vez por dia; não obriga escrita em cada leitura.
            if epoch - self.last_cleanup >= 86400:
                self.conn.execute('DELETE FROM samples WHERE ts < ?',
                                  (epoch - self.retention_days * 86400,))
                self.last_cleanup = epoch
            self.conn.commit()

    def history(self, metric: str, range_name: str, now: float | None = None, max_points: int = 240):
        if metric not in METRICS or range_name not in RANGES:
            raise ValueError('metric ou range inválido')
        span = RANGES[range_name]
        end = now if now is not None else time.time()
        start = end - span
        bucket = max(1, (span + max_points - 1) // max_points)
        with self.lock:
            records = self.conn.execute('''
                SELECT CAST((ts - ?) / ? AS INTEGER) AS bucket, AVG(value)
                  FROM samples WHERE metric = ? AND ts >= ? AND ts <= ?
                 GROUP BY bucket ORDER BY bucket ASC
            ''', (start, bucket, metric, start, end)).fetchall()
        return [{'time': round((start + group * bucket) * 1000), 'value': round(value, 4)}
                for group, value in records]

    def close(self):
        with self.lock:
            self.conn.close()
