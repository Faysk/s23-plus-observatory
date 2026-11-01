"""Histórico SQLite com retenção explícita e buckets sem interpolação."""
from __future__ import annotations
import datetime as dt
import json
import math
import sqlite3
import threading
import time
from pathlib import Path
from .catalog import DEFINITIONS

RANGES = {'1h': 3600, '6h': 21600, '12h': 43200, '24h': 86400,
          '7d': 604800, '30d': 2592000, '90d': 7776000}
METRICS = set(DEFINITIONS)


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
        self.conn.execute('CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, ts REAL NOT NULL UNIQUE, payload TEXT NOT NULL)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS snapshots_ts ON snapshots(ts)')
        self.conn.commit()
        self.lock = threading.Lock()
        self.retention_days = retention_days
        self.last_cleanup = 0.0

    def record(self, epoch: float, values: dict[str, float], snapshot=None):
        rows = [(epoch, name, value) for name, value in values.items() if name in METRICS
                and isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)]
        with self.lock, self.conn:
            if snapshot is not None:
                self.conn.execute('INSERT INTO snapshots(ts,payload) VALUES (?,?)',
                                  (epoch, json.dumps(snapshot, ensure_ascii=False, allow_nan=False)))
            if rows:
                self.conn.executemany('INSERT OR REPLACE INTO samples(ts, metric, value) VALUES (?, ?, ?)', rows)
            # Apaga somente uma vez por dia; não obriga escrita em cada leitura.
            if epoch - self.last_cleanup >= 86400:
                self.conn.execute('DELETE FROM samples WHERE ts < ?',
                                  (epoch - self.retention_days * 86400,))
                self.conn.execute('DELETE FROM snapshots WHERE ts < ?', (epoch - self.retention_days * 86400,))
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
                SELECT CAST((ts - ?) / ? AS INTEGER) AS bucket, AVG(value), MIN(value), MAX(value), COUNT(*), MIN(ts), MAX(ts), MAX(ts-previous)
                  FROM (SELECT ts, value, LAG(ts) OVER (ORDER BY ts) AS previous
                          FROM samples WHERE metric = ? AND ts >= ? AND ts <= ?)
                 GROUP BY bucket ORDER BY bucket ASC
            ''', (start, bucket, metric, start, end)).fetchall()
        return [{'time': round(last * 1000), 'value': round(value, 4), 'min': low, 'max': high,
                 'count': count, 'firstTime': round(first * 1000), 'lastTime': round(last * 1000), 'maxGapSec': gap}
                for group, value, low, high, count, first, last, gap in records]

    def summary(self, metric, range_name, now=None):
        if metric not in METRICS or range_name not in RANGES:
            raise ValueError('metric ou range inválido')
        end = now if now is not None else time.time()
        with self.lock:
            count, low, high, avg, first, last = self.conn.execute(
                'SELECT COUNT(*), MIN(value), MAX(value), AVG(value), MIN(ts), MAX(ts) FROM samples WHERE metric=? AND ts BETWEEN ? AND ?',
                (metric, end-RANGES[range_name], end)).fetchone()
        return dict(count=count, min=low, max=high, mean=avg,
                    firstTime=round(first*1000) if first is not None else None,
                    lastTime=round(last*1000) if last is not None else None)

    def archive(self, after=0, limit=50):
        if after < 0 or not 1 <= limit <= 100:
            raise ValueError('cursor ou limite inválido')
        with self.lock:
            rows = self.conn.execute('SELECT id,ts,payload FROM snapshots WHERE id>? ORDER BY id LIMIT ?', (after, limit)).fetchall()
        return dict(records=[dict(id=i, timestamp=ts, snapshot=json.loads(payload)) for i, ts, payload in rows],
                    nextCursor=rows[-1][0] if rows else after)

    def info(self):
        with self.lock:
            count, first, last = self.conn.execute('SELECT COUNT(*), MIN(ts), MAX(ts) FROM snapshots').fetchone()
        return dict(snapshots=count, firstSample=first, lastSample=last, retentionDays=self.retention_days)

    def close(self):
        with self.lock:
            self.conn.close()
