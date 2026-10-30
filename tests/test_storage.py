import tempfile
import unittest
from pathlib import Path
from observatory.storage import Storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Storage(str(Path(self.tmp.name) / 'data.sqlite3'),retention_days=90)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_missing_zero_and_order(self):
        now=1_800_000_000
        self.db.record(now-120,{'battery':0.0,'cpu':24.5})
        self.db.record(now-60,{'battery':10.0,'cpu':None} if False else {'battery':10.0})
        pts=self.db.history('battery','1h',now=now)
        self.assertEqual([p['value'] for p in pts],[0.0,10.0])
        self.assertEqual(self.db.history('temp','1h',now=now),[])

    def test_reject_unknown_queries(self):
        with self.assertRaises(ValueError):self.db.history('invalid','24h')
        with self.assertRaises(ValueError):self.db.history('cpu','forever')

    def test_retention(self):
        now=1_800_000_000
        self.db.record(now-91*86400,{'cpu':20})
        self.db.record(now,{'cpu':30})
        count=self.db.conn.execute('select count(*) from samples where metric=?',('cpu',)).fetchone()[0]
        self.assertEqual(count,1)

if __name__=='__main__': unittest.main()
