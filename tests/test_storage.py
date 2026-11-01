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

    def test_aggregation_preserves_spikes_and_exact_summary(self):
        now=1_800_000_000
        self.db.record(now-12, {'cpu':5})
        self.db.record(now-10, {'cpu':95})
        points=self.db.history('cpu','1h',now=now)
        self.assertEqual(len(points),1)
        self.assertEqual((points[0]['value'],points[0]['min'],points[0]['max'],points[0]['count']), (50,5,95,2))
        self.assertEqual(points[0]['time'],(now-10)*1000)
        self.assertEqual(self.db.summary('cpu','1h',now=now)['mean'],50)

    def test_complete_archive_pagination_and_reopen(self):
        now=1_800_000_000
        raw={'cpu':{'usagePercent':None},'battery':{'levelPercent':0},'diagnostics':{'source':'synthetic'}}
        self.db.record(now,{'cpu':None,'battery':0,'tx':float('nan')},raw)
        self.db.record(now+30,{'battery':1},raw)
        first=self.db.archive(0,1)
        self.assertEqual(first['records'][0]['snapshot'],raw)
        second=self.db.archive(first['nextCursor'],1)
        self.assertGreater(second['nextCursor'],first['nextCursor'])
        self.assertEqual(self.db.info()['snapshots'],2)
        with self.assertRaises(ValueError):self.db.archive(0,101)
        path=str(Path(self.tmp.name)/'data.sqlite3')
        self.db.close();self.db=Storage(path)
        self.assertEqual(self.db.archive(0,1)['records'][0]['snapshot'],raw)

if __name__=='__main__': unittest.main()
