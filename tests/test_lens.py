"""Synthetic Linux regressions. No network, privilege or real log data needed."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

TOOL=Path(__file__).resolve().parents[1]/'tools/server-lens/server-lens'

@unittest.skipUnless(os.name=='posix' and Path('/proc').exists(),'Linux only')
class LensTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.bin=self.root/'bin';self.bin.mkdir()
  self.proc=self.root/'proc';self.proc.mkdir();self.cg=self.root/'cg';self.cg.mkdir()
  self.logs=self.root/'logs';self.logs.mkdir()
  for name in ['awk','uname','date','tail','cat']:
   found=shutil.which(name)
   if not found:self.skipTest(name+' required for test runner')
   (self.bin/name).symlink_to(found)
  self.put('meminfo','MemTotal: 3000000 kB\nMemAvailable: 1000000 kB\nSwapTotal: 1000 kB\nSwapFree: 700 kB\n')
  self.put('stat','cpu 100 0 100 800 0 0 0 0 50 0\n')
  self.put('stat.next','cpu 150 0 100 850 0 0 0 0 90 0\n')
  self.put('cpuinfo','processor : 0\nmodel name : Fixture CPU\nprocessor : 1\n')
  self.put('uptime','90061.00 400.0\n');self.put('loadavg','0.1 0.2 0.3 1/100 111\n')
  cp=shutil.which('cp')
  self.command('sleep',f'"{cp}" "$SERVER_LENS_PROC_ROOT/stat.next" "$SERVER_LENS_PROC_ROOT/stat"')
  self.command('df',"cat <<'EOF'\nFilesystem 1024-blocks Used Available Capacity Mounted on\n/dev/root 100000 20000 80000 20% /\n/dev/data 200000 190000 10000 95% /srv/my data\ntmpfs 1000 50 950 5% /run\nEOF")
  self.env={**os.environ,'PATH':str(self.bin),'SERVER_LENS_PROC_ROOT':str(self.proc),'SERVER_LENS_CGROUP_ROOT':str(self.cg),'SERVER_LENS_LOG_ROOT':str(self.logs),'COLUMNS':'80','TERM':'dumb'}
 def put(self,name,text):
  (self.proc/name).write_text(text)
 def command(self,name,text):
  path=self.bin/name
  if path.is_symlink():path.unlink()
  path.write_text('#!/bin/sh\n'+text+'\n');path.chmod(0o755)
 def run_tool(self,*args,check=True):
  result=subprocess.run(['/bin/sh',str(TOOL),*args],env=self.env,text=True,capture_output=True,timeout=15)
  if check:self.assertEqual(result.returncode,0,result.stderr)
  return result
 def report(self):return json.loads(self.run_tool('--json').stdout)
 def test_cpu_sample_excludes_guest_double_count(self):
  self.assertEqual(self.report()['cpu']['percent'],50.0)
 def test_memory_available_and_swap(self):
  r=self.report();self.assertEqual(r['memory']['used_kib'],2000000);self.assertEqual(r['memory']['swap_used_kib'],300)
 def test_legacy_memory_estimate(self):
  self.put('meminfo','MemTotal: 1000 kB\nMemFree: 100 kB\nBuffers: 20 kB\nCached: 300 kB\nSReclaimable: 50 kB\nShmem: 30 kB\n')
  r=self.report()['memory'];self.assertEqual(r['available_kib'],440);self.assertEqual(r['method'],'estimated')
 def test_clamp_legacy_memory(self):
  self.put('meminfo','MemTotal: 100 kB\nMemFree: 500 kB\n');self.assertEqual(self.report()['memory']['used_kib'],0)
 def test_mount_path_with_spaces_and_tmpfs_filter(self):
  d=self.report()['disks'];self.assertEqual(len(d),2);self.assertEqual(d[1]['mount'],'/srv/my data');self.assertEqual(d[1]['percent'],95)
 def test_no_optional_probes_is_unknown(self):
  r=self.report();self.assertEqual(r['time']['status'],'unknown');self.assertEqual(r['logins']['status'],'unavailable')
 def test_enabled_ntp_does_not_mean_synchronized(self):
  self.command('timedatectl',"printf 'NTP=yes\\nNTPSynchronized=no\\nTimezone=UTC\\n'")
  self.assertEqual(self.report()['time']['status'],'unsynchronized')
 def test_systemd_synchronized(self):
  self.command('timedatectl',"printf 'NTP=yes\\nNTPSynchronized=yes\\nTimezone=UTC\\n'")
  self.assertEqual(self.report()['time']['status'],'synchronized')
 def test_chrony_local_reference_is_not_external(self):
  self.command('chronyc',"printf 'Reference ID : 7F7F0101 ()\\nLeap status : Normal\\n'")
  self.assertEqual(self.report()['time']['status'],'local-reference')
 def test_chrony_unsynchronized(self):
  self.command('chronyc',"printf 'Reference ID : 00000000 ()\\nLeap status : Not synchronised\\n'")
  self.assertEqual(self.report()['time']['status'],'unsynchronized')
 def test_chrony_selected_reference(self):
  self.command('chronyc',"printf 'Reference ID : C0000201 (192.0.2.1)\\nLeap status : Normal\\n'")
  self.assertEqual(self.report()['time']['status'],'synchronized')
 def test_ntpd_selected_peer(self):
  self.command('ntpq',"printf '*192.0.2.1 .GPS. 1 u 10 64 377 1.0 0.1 0.1\\n'")
  self.assertEqual(self.report()['time']['status'],'synchronized')
 def test_log_json_escaping_and_terminal_control_sanitization(self):
  self.command('last',"printf 'alice pts/0 host\\033[31m Thu Oct 22 12:00:00 2026 \\\"quoted\\\" \\\\path\\n'")
  r=self.report();line=r['logins']['entries'][0];self.assertIn('alice',line);self.assertNotIn('\x1b',line)
  self.assertNotIn('\x1b',self.run_tool('--plain').stdout)
 def test_wtmpdb_fallback(self):
  self.command('wtmpdb',"printf 'alice pts/0 192.0.2.2 Thu Oct 22 12:00:00 2026\\n'")
  r=self.report();self.assertEqual(r['logins']['source'],'wtmpdb');self.assertIn('2026',r['logins']['entries'][0])
 def test_ssh_journal_success_only_newest_first(self):
  self.command('journalctl',"printf '2026-10-22T10:00:00 sshd Accepted publickey for alice\\n2026-10-22T10:01:00 sshd Failed password for root\\n2026-10-22T10:02:00 sshd Accepted password for bob\\n'")
  r=self.report()['logins'];self.assertEqual(len(r['entries']),2);self.assertIn('bob',r['entries'][0]);self.assertEqual(r['source'],'sshd-journal')
 def test_cgroup_limits_are_separate(self):
  (self.cg/'memory.max').write_text('1048576\n');(self.cg/'memory.current').write_text('524288\n');(self.cg/'cpu.max').write_text('50000 100000\n')
  r=self.report();self.assertEqual(r['memory']['cgroup_limit_kib'],1024);self.assertEqual(r['memory']['total_kib'],3000000);self.assertEqual(r['cpu']['cgroup_quota_cores'],0.5)
 def test_unlimited_cgroup_is_not_zero(self):
  (self.cg/'memory.max').write_text('max\n');self.assertIsNone(self.report()['memory']['cgroup_limit_kib'])
 def test_cgroup_v1_unlimited_sentinel(self):
  (self.cg/'memory.limit_in_bytes').write_text('9223372036854771712\n');self.assertIsNone(self.report()['memory']['cgroup_limit_kib'])
 def test_json_redaction(self):
  self.command('last',"printf 'alice pts/0 192.0.2.2 Thu Oct 22 12:00:00 2026\\n'")
  r=json.loads(self.run_tool('--json','--redact').stdout);s=json.dumps(r)
  self.assertTrue(r['redacted']);self.assertNotIn('alice',s);self.assertNotIn('192.0.2.2',s);self.assertNotIn('/srv/my data',s)
 def test_unavailable_cpu_is_null(self):
  self.put('stat','cpu 0 0 0 0\n');self.put('stat.next','cpu 0 0 0 0\n');self.assertIsNone(self.report()['cpu']['percent'])
 def test_width_and_piped_escape_safety(self):
  self.env['COLUMNS']='40';s=self.run_tool('--plain').stdout
  self.assertTrue(all(len(line)<=40 for line in s.splitlines()));self.assertNotIn('\x1b',s)
 def test_invalid_options_and_non_tty_watch(self):
  for args in [('--interval','0'),('--interval','no'),('--logins','51'),('--wat',),('--watch',),('--watch','--json')]:
   self.assertEqual(self.run_tool(*args,check=False).returncode,2,args)
 def test_fixture_is_explicit_and_proc_files_unchanged(self):
  before=(self.proc/'meminfo').read_bytes();r=self.report();self.assertEqual(r['data_source'],'fixture');self.assertEqual((self.proc/'meminfo').read_bytes(),before)
 def test_help_and_version(self):
  self.assertIn('--redact',self.run_tool('--help').stdout);self.assertEqual(self.run_tool('--version').stdout.strip(),'1.0.0')

if __name__=='__main__':unittest.main()
