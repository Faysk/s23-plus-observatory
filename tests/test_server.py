import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from observatory.server import State, handler_factory
from observatory.storage import Storage


class FakeCollector:
    def collect(self):
        return {'source':'live','timestamp':'2026-10-30T00:00:00+00:00','device':{},
                'cpu':{'usagePercent':0}, 'memory':{'usedMB':40,'totalMB':100},
                'battery':{'levelPercent':70,'temperatureC':None},
                'network':{'rxMbps':None,'txMbps':0},'storage':[{'usedPercent':20}]}


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.storage=Storage(str(Path(self.tmp.name)/'metrics.db'))
        self.state=State(FakeCollector(),self.storage,30)
        self.state.sample()
        self.httpd=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(self.state))
        self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True)
        self.thread.start()
        self.base='http://127.0.0.1:'+str(self.httpd.server_port)

    def tearDown(self):
        self.httpd.shutdown();self.httpd.server_close();self.thread.join()
        self.state.close();self.tmp.cleanup()

    def get(self,path):
        with urllib.request.urlopen(self.base+path,timeout=3) as r:return r.status,dict(r.headers),r.read()

    def test_live_snapshot_and_history(self):
        code,headers,body=self.get('/api/host/snapshot')
        self.assertEqual(code,200)
        self.assertEqual(headers['Access-Control-Allow-Origin'] if 'Access-Control-Allow-Origin' in headers else None,None)
        self.assertEqual(json.loads(body)['cpu']['usagePercent'],0)
        data=json.loads(self.get('/api/host/history?metric=cpu&range=1h')[2])
        self.assertEqual(data['points'][0]['value'],0)

    def test_api_invalid_query_and_read_only(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get('/api/host/history?metric=hello&range=24h')
        self.assertEqual(ctx.exception.code,400)
        req=urllib.request.Request(self.base+'/api/host/snapshot',data=b'{}',method='POST')
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code,405)

    def test_static_and_path_traversal(self):
        self.assertEqual(self.get('/')[0],200)
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.get('/../README.md')
        self.assertEqual(ctx.exception.code,404)

if __name__=='__main__':unittest.main()
