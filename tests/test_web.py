import importlib.util,json,math,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
path=Path(__file__).resolve().parents[1]/'tools/server-lens-web/server.py'
spec=importlib.util.spec_from_file_location('lens_web',path);web=importlib.util.module_from_spec(spec);spec.loader.exec_module(web)
class FakeMetrics(web.Metrics):
 def __init__(self):super().__init__();self.calls=0;self.overrides={}
 def query(self,expression,span=None):
  self.calls+=1
  if span:return [[100,12.0],[160,None],[220,15.0]]
  key=next(k for k,v in web.QUERIES.items() if v==expression)
  values={'up':1,'cpu_percent':12.5,'cores':4,'memory_total':1000,'memory_available':600,'disk_total':2000,'disk_available':500,'uptime':10000,'collector_ok':1,'sample_age':2}
  return self.overrides.get(key,values[key])
class MetricTests(unittest.TestCase):
 def test_nonfinite_is_unknown(self):
  for v in ['NaN','+Inf','-Inf',None,'bad']:self.assertIsNone(web.finite(v))
 def test_percent_missing_and_clamping(self):
  self.assertIsNone(web.percent(None,1));self.assertIsNone(web.percent(0,0));self.assertEqual(web.percent(120,100),0);self.assertEqual(web.percent(-2,100),100)
 def test_snapshot_and_cache(self):
  m=FakeMetrics();a=m.snapshot();self.assertEqual(a['status'],'ready');self.assertEqual(a['memory']['percent'],40);self.assertEqual(a['disk']['percent'],75);count=m.calls;self.assertEqual(m.snapshot(),a);self.assertEqual(m.calls,count)
 def test_stale_sample_is_not_healthy(self):
  m=FakeMetrics();m.overrides['sample_age']=100;self.assertEqual(m.snapshot()['status'],'unavailable')
 def test_cpu_needs_samples(self):
  m=FakeMetrics();m.overrides['cpu_percent']=None;r=m.snapshot();self.assertEqual(r['status'],'warming_up');self.assertIsNone(r['cpu']['percent'])
 def test_partial_missing_memory(self):
  m=FakeMetrics();m.overrides['memory_available']=None;r=m.snapshot();self.assertEqual(r['status'],'partial');self.assertIsNone(r['memory']['percent'])
 def test_collector_error_not_ready(self):
  m=FakeMetrics();m.overrides['collector_ok']=0;self.assertEqual(m.snapshot()['status'],'unavailable')
 def test_upstream_failure_never_demo(self):
  m=web.Metrics()
  with patch.object(m,'query',side_effect=OSError('offline')):r=m.snapshot()
  self.assertEqual(r['source'],'prometheus');self.assertEqual(r['status'],'unavailable');self.assertIsNone(r['cpu']['percent']);json.dumps(r,allow_nan=False)
 def test_prometheus_must_be_loopback(self):
  for url in ['http://example.com:9090','http://127.0.0.1:9090/x','http://user:pass@127.0.0.1:9090','file:///etc/passwd']:
   with self.assertRaises(ValueError):web.Metrics(url)
 def test_ranges_are_allowlisted(self):
  with self.assertRaises(ValueError):FakeMetrics().snapshot('1y')
class GatewayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=web.Server(('127.0.0.1',0),FakeMetrics());cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def get(self,path,headers=None):return urlopen(Request(self.url+path,headers=headers or {}),timeout=5)
 def test_json_and_security_headers(self):
  with self.get('/api/summary') as r:
   self.assertEqual(json.load(r)['source'],'prometheus');self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy'])
 def test_no_arbitrary_query_proxy(self):
  for path in ['/api/summary?query=up','/api/summary?range=1y','/api/summary?range=1h&range=24h','/api/v1/query?query=up','/../../etc/passwd']:
   with self.assertRaises(HTTPError) as error:self.get(path)
   self.assertIn(error.exception.code,[400,404])
 def test_external_host_rejected(self):
  with self.assertRaises(HTTPError) as error:self.get('/',{'Host':'evil.example'})
  self.assertEqual(error.exception.code,403)
 def test_malformed_host_returns_bad_request(self):
  with self.assertRaises(HTTPError) as error:self.get('/',{'Host':'[broken'})
  self.assertEqual(error.exception.code,400)
 def test_live_index_and_static_allowlist(self):
  with self.get('/') as r:self.assertIn(b'data-source="prometheus"',r.read())
  with self.assertRaises(HTTPError):self.get('/demo.html')
 def test_health(self):
  with self.get('/healthz') as r:self.assertEqual(json.load(r),{'web':'ready'})
if __name__=='__main__':unittest.main()
