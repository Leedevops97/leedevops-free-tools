#!/usr/bin/env python3
"""Server Lens Web 1.1.0. A loopback-only, fixed-query Prometheus gateway."""
import argparse
import concurrent.futures
import datetime
import json
import math
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

VERSION='1.1.0'
ROOT=Path(__file__).resolve().parent/'ui'
JOB='{job="server_lens"}'
QUERIES={
 'up':'up'+JOB,
 'cpu_percent':'100 * (1 - avg(rate(node_cpu_seconds_total{job="server_lens",mode="idle"}[2m])))',
 'cores':'count(node_cpu_seconds_total{job="server_lens",mode="idle"})',
 'memory_total':'node_memory_MemTotal_bytes'+JOB,
 'memory_available':'node_memory_MemAvailable_bytes'+JOB,
 'disk_total':'max(node_filesystem_size_bytes{job="server_lens",mountpoint="/"})',
 'disk_available':'min(node_filesystem_avail_bytes{job="server_lens",mountpoint="/"})',
 'uptime':'time() - node_boot_time_seconds'+JOB,
 'collector_ok':'min(node_scrape_collector_success'+JOB+')',
 'sample_age':'time() - timestamp(node_memory_MemTotal_bytes'+JOB+')',
}
HISTORY={
 'cpu':QUERIES['cpu_percent'],
 'memory':'100 * (1 - node_memory_MemAvailable_bytes{job="server_lens"} / node_memory_MemTotal_bytes{job="server_lens"})',
 'disk':'100 * (1 - min(node_filesystem_avail_bytes{job="server_lens",mountpoint="/"}) / max(node_filesystem_size_bytes{job="server_lens",mountpoint="/"}))',
}
RANGES={'1h':(3600,60),'6h':(21600,300),'24h':(86400,900)}

def finite(value):
 try:
  value=float(value)
  return value if math.isfinite(value) else None
 except (TypeError,ValueError):return None

def percent(available,total):
 if available is None or total is None or total<=0:return None
 return round(max(0,min(100,100*(1-available/total))),2)

class Metrics:
 def __init__(self,base='http://127.0.0.1:19090'):
  parsed=urlsplit(base)
  if parsed.scheme!='http' or parsed.hostname not in ['127.0.0.1','localhost','::1'] or parsed.username or parsed.password or parsed.path not in ['', '/']:
   raise ValueError('Prometheus must be an HTTP loopback address without credentials/path')
  self.base=base.rstrip('/');self.cache={};self.lock=threading.Lock()
 def query(self,expression,span=None):
  params={'query':expression,'timeout':'3s'};endpoint='query'
  if span:
   duration,step=RANGES[span];end=int(time.time());params.update(start=end-duration,end=end,step=step);endpoint='query_range'
  req=Request(self.base+'/api/v1/'+endpoint+'?'+urlencode(params),headers={'User-Agent':'ServerLensWeb/'+VERSION})
  with urlopen(req,timeout=4) as response:
   raw=response.read(1_000_001)
   if len(raw)>1_000_000:raise ValueError('Oversized upstream result')
   payload=json.loads(raw)
  if payload.get('status')!='success':raise ValueError('Prometheus query failed')
  rows=payload.get('data',{}).get('result',[])
  if span:
   return [[float(t),finite(v)] for t,v in rows[0].get('values',[])] if rows else []
  return finite(rows[0].get('value',[None,None])[1]) if rows else None
 def snapshot(self,span='1h'):
  if span not in RANGES:raise ValueError('Unsupported range')
  with self.lock:
   cached=self.cache.get(span)
   if cached and time.monotonic()-cached[0]<25:return cached[1]
   values={};errors=[]
   def fetch(name,expression,history=False):
    try:return name,self.query(expression,span if history else None),None
    except Exception:return name,[] if history else None,'unavailable'
   # At most four upstream requests at a time, all from a fixed allowlist.
   with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(fetch,k,v) for k,v in QUERIES.items()]
    futures += [pool.submit(fetch,'history_'+k,v,True) for k,v in HISTORY.items()]
    for future in concurrent.futures.as_completed(futures):
     name,value,error=future.result();values[name]=value
     if error:errors.append(name)
   current=values.get('sample_age');status='ready'
   if errors or values.get('up')!=1 or values.get('collector_ok')!=1 or current is None or current>90:status='unavailable'
   elif values.get('cpu_percent') is None:status='warming_up'
   if status=='ready' and any(values.get(k) is None for k in ['memory_total','memory_available','disk_total','disk_available','uptime']):status='partial'
   payload={
    'version':VERSION,'source':'prometheus','status':status,
    'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sample_age_seconds':current,'refresh_seconds':30,'range':span,
    'cpu':{'percent':values.get('cpu_percent'),'cores':values.get('cores')},
    'memory':{'total_bytes':values.get('memory_total'),'available_bytes':values.get('memory_available'),'percent':percent(values.get('memory_available'),values.get('memory_total'))},
    'disk':{'total_bytes':values.get('disk_total'),'available_bytes':values.get('disk_available'),'percent':percent(values.get('disk_available'),values.get('disk_total'))},
    'uptime_seconds':values.get('uptime'),
    'history':{k:values.get('history_'+k,[]) for k in HISTORY},
   }
   self.cache[span]=(time.monotonic(),payload)
   return payload

class Handler(BaseHTTPRequestHandler):
 server_version='ServerLensWeb/'+VERSION
 def log_message(self,*args):pass
 def send(self,status,data,kind='application/json'):
  self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8')
  self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store' if kind=='application/json' else 'no-cache')
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
  self.end_headers()
  if self.command!='HEAD':self.wfile.write(data)
 def do_HEAD(self):self.do_GET()
 def do_GET(self):
  try:host=urlsplit('//'+self.headers.get('Host','')).hostname
  except ValueError:return self.send(400,b'{"error":"invalid host"}')
  if host not in ['localhost','127.0.0.1','::1']:return self.send(403,b'{"error":"loopback host required"}')
  path=urlsplit(self.path)
  if path.path=='/healthz':return self.send(200,b'{"web":"ready"}')
  if path.path=='/api/summary':
   args=parse_qs(path.query);span=args.get('range',['1h'])
   if set(args)-{'range'} or len(span)!=1 or span[0] not in RANGES:return self.send(400,b'{"error":"unsupported parameters"}')
   data=self.server.metrics.snapshot(span[0])
   return self.send(200,json.dumps(data,allow_nan=False,separators=(',',':')).encode())
  files={'/':('index.html','text/html'),'/index.html':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
  if path.path not in files:return self.send(404,b'{"error":"not found"}')
  name,kind=files[path.path];self.send(200,(ROOT/name).read_bytes(),kind)

class Server(ThreadingHTTPServer):
 daemon_threads=True
 request_queue_size=8
 def __init__(self,address,metrics):
  self.slots=threading.BoundedSemaphore(8);self.metrics=metrics;super().__init__(address,Handler)
 def process_request(self,request,address):
  if not self.slots.acquire(blocking=False):self.shutdown_request(request);return
  request.settimeout(15)
  try:super().process_request(request,address)
  except Exception:self.slots.release();raise
 def process_request_thread(self,request,address):
  try:super().process_request_thread(request,address)
  finally:self.slots.release()

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18790);p.add_argument('--prometheus',default='http://127.0.0.1:19090');args=p.parse_args()
 if not 1024<=args.port<=65535:p.error('port must be 1024..65535')
 server=Server(('127.0.0.1',args.port),Metrics(args.prometheus))
 print('Server Lens Web listening at http://127.0.0.1:'+str(args.port),flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=='__main__':main()
