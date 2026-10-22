#!/usr/bin/env python3
"""Install the reviewed systemd addon. No pip/npm/Docker dependencies."""
import argparse,datetime,gzip,hashlib,json,os,platform,shutil,socket,subprocess,tarfile,tempfile,urllib.request
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
DEST=Path('/opt/leedevops/server-lens-web')
UNITS=Path('/etc/systemd/system')
NAMES=['leedevops-node-exporter','leedevops-prometheus','leedevops-server-lens-web']
def run(args):return subprocess.run(args,text=True,capture_output=True,check=True).stdout
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def unit(name,description,command,memory,extra='',env=''):
 return f'''[Unit]
Description={description}
After=network.target

[Service]
Type=simple
DynamicUser=yes
ExecStart={command}
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
MemoryMax={memory}
TasksMax=64
CPUQuota=25%
{env}
{extra}

[Install]
WantedBy=multi-user.target
'''
def acquire(repo,lock,cache,arch):
 info=lock[repo];target=cache/repo
 if target.exists() and info.get('binary_sha256',{}).get(arch)==digest(target):return target
 compressed=cache/(repo+'.gz')
 if compressed.exists() and arch in info.get('binary_sha256',{}):
  with gzip.open(compressed,'rb') as src,target.open('wb') as out:shutil.copyfileobj(src,out)
  if digest(target)!=info['binary_sha256'][arch]:raise RuntimeError('Cached binary checksum mismatch')
  return target
 asset=info['assets'][arch];archive=cache/asset['name'];expected=asset['digest'].removeprefix('sha256:')
 if not archive.exists() or digest(archive)!=expected:
  req=urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'ServerLensWeb/1.1.0'})
  print('Downloading official '+asset['name'],flush=True)
  with urllib.request.urlopen(req,timeout=60) as src,archive.with_suffix('.part').open('wb') as out:shutil.copyfileobj(src,out)
  archive.with_suffix('.part').replace(archive)
 if digest(archive)!=expected:raise RuntimeError('Official archive checksum mismatch')
 with tarfile.open(archive,'r:gz') as tar:
  member=next(x for x in tar.getmembers() if x.isfile() and x.name.endswith('/'+repo))
  if member.size>350_000_000:raise RuntimeError('Unexpected binary size')
  with tar.extractfile(member) as src,target.open('wb') as out:shutil.copyfileobj(src,out)
 return target
def main():
 p=argparse.ArgumentParser(description='Install private Server Lens Web, Prometheus and Node Exporter')
 p.add_argument('--binary-cache',type=Path,default=Path('/var/cache/leedevops-server-lens-web'))
 args=p.parse_args()
 if platform.system()!='Linux' or not Path('/run/systemd/system').is_dir():p.error('This installer requires Linux with systemd; see manual deployment documentation')
 if os.geteuid()!=0:p.error('Run the inspected installer with sudo')
 arch={'x86_64':'amd64','aarch64':'arm64'}.get(platform.machine())
 if not arch:p.error('Supported binary architectures: x86_64 and aarch64')
 if (DEST/'installation.json').exists():
  print('Managed installation already exists; settings and data preserved.');print(run(['systemctl','is-active',*NAMES]));return
 if DEST.exists() or any((UNITS/(n+'.service')).exists() for n in NAMES):raise RuntimeError('Existing unmanaged files found; inspect before installing')
 for port in [18790,19090,19100]:
  with socket.socket() as test:test.bind(('127.0.0.1',port))
 args.binary_cache.mkdir(parents=True,exist_ok=True)
 lock=json.loads((SOURCE/'release-lock.json').read_text())
 binaries={repo:acquire(repo,lock,args.binary_cache,arch) for repo in ['prometheus','node_exporter']}
 for path in binaries.values():path.chmod(0o755);print(run([str(path),'--version']).splitlines()[0])
 # All downloads/checks complete before creating services.
 DEST.mkdir(parents=True);(DEST/'bin').mkdir();(DEST/'ui').mkdir();shutil.copytree(SOURCE/'licenses',DEST/'licenses')
 for repo,path in binaries.items():shutil.copyfile(path,DEST/'bin'/repo);(DEST/'bin'/repo).chmod(0o755)
 for name in ['server.py','prometheus.yml','release-lock.json']:
  shutil.copyfile(SOURCE/name,DEST/name);(DEST/name).chmod(0o644)
 for name in ['index.html','style.css','app.js']:
  shutil.copyfile(SOURCE/'ui'/name,DEST/'ui'/name);(DEST/'ui'/name).chmod(0o644)
 configs={
 NAMES[0]:unit(NAMES[0],'Server Lens limited Node Exporter',str(DEST/'bin/node_exporter')+' --web.listen-address=127.0.0.1:19100 --web.disable-exporter-metrics --collector.disable-defaults --collector.cpu --collector.meminfo --collector.filesystem --collector.stat --collector.time --collector.loadavg --collector.filesystem.mount-points-include=^/$ --log.level=warn','64M',env='Environment=GOMEMLIMIT=32MiB'),
 NAMES[1]:unit(NAMES[1],'Server Lens Prometheus',str(DEST/'bin/prometheus')+' --config.file='+str(DEST/'prometheus.yml')+' --web.listen-address=127.0.0.1:19090 --storage.tsdb.path=/var/lib/leedevops-prometheus --storage.tsdb.retention.time=2d --storage.tsdb.retention.size=128MB --query.max-concurrency=4 --query.max-samples=200000 --query.timeout=5s --web.max-connections=32 --log.level=warn','256M',extra='StateDirectory=leedevops-prometheus\nStateDirectoryMode=0700',env='Environment=GOMEMLIMIT=96MiB'),
 NAMES[2]:unit(NAMES[2],'Server Lens private web dashboard','/usr/bin/python3 '+str(DEST/'server.py')+' --port=18790','64M',env='Environment=PYTHONDONTWRITEBYTECODE=1\nEnvironment=PYTHONUNBUFFERED=1'),
 }
 hashes={}
 for name,content in configs.items():
  path=UNITS/(name+'.service');path.write_text(content);path.chmod(0o644);hashes[str(path)]=digest(path)
 metadata={'version':'1.1.0','installed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'architecture':arch,'binaries':{k:digest(v) for k,v in binaries.items()},'unit_hashes':hashes,'ports':{'web':18790,'prometheus':19090,'exporter':19100},'all_bindings':'127.0.0.1'}
 (DEST/'installation.json').write_text(json.dumps(metadata,indent=2));(DEST/'installation.json').chmod(0o644)
 run(['systemctl','daemon-reload']);run(['systemctl','enable','--now',*NAMES]);print(run(['systemctl','is-active',*NAMES]))
 print('Private dashboard: http://127.0.0.1:18790 (SSH tunnel required).')
if __name__=='__main__':main()
