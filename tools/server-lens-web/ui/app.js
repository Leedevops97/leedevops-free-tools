(() => {'use strict';
const demo = document.documentElement.dataset.source === 'demo';
const $ = id => document.getElementById(id);
const copy = {
en:{demo:'INTERACTIVE DEMO · All values are simulated. No real server data.',overview:'YOUR SERVER / OVERVIEW',headline:'Clarity. In real time.',intro:'Just the essentials. A little less noise.',pause:'Pause',resume:'Resume',refresh:'Refresh ↻',connecting:'Connecting',cadence:'30s collection · 48h retention',cpu:'CPU usage',memory:'Memory',disk:'Root disk',uptime:'Uptime',since_boot:'Since the last system boot',trend:'A LITTLE PERSPECTIVE',history:'Resource history',range:'Time range',utilization:'Utilization',no_history:'History will appear after the first samples.',now:'Now',available_memory:'Available memory',available_disk:'Disk available to applications',collection:'Collection',collection_value:'Prometheus · Node Exporter',data_note:'Memory uses MemAvailable. Disk usage includes reserved space unavailable to applications. Missing or stale metrics are never shown as zero.',footer:'Small footprint. Clear signals.',about:'About this tool ↗',ready:'All systems reporting',warming_up:'Collecting first samples',unavailable:'Data unavailable / stale',partial:'Some metrics unavailable',simulated:'Simulated data',updated:'Updated',used:'used',total:'total',cores:'logical cores',paused:'Refresh paused',boot:'Boot',normal:'Normal',check:'Elevated',high:'High',demo_collection:'Browser simulation · no data connection'},
zh:{demo:'交互演示 · 所有数值均为模拟数据，不包含真实服务器信息。',overview:'你的服务器 / 概览',headline:'状态清晰，尽在眼前。',intro:'只留基础信息，减少监控噪音。',pause:'暂停',resume:'继续',refresh:'刷新 ↻',connecting:'正在连接',cadence:'30 秒采集 · 保留 48 小时',cpu:'CPU 使用率',memory:'内存',disk:'根磁盘',uptime:'运行时长',since_boot:'距离上次系统启动',trend:'看见变化',history:'资源趋势',range:'时间范围',utilization:'使用率',no_history:'首批采样完成后显示趋势。',now:'现在',available_memory:'可用内存',available_disk:'应用可用磁盘空间',collection:'数据采集',collection_value:'Prometheus · Node Exporter',data_note:'内存基于 MemAvailable。磁盘占用包含应用不可用的保留空间。缺失或过期数据不会显示为零。',footer:'轻量运行，清晰呈现。',about:'了解这个工具 ↗',ready:'各项指标正常上报',warming_up:'正在采集首批数据',unavailable:'数据不可用或已过期',partial:'部分指标不可用',simulated:'模拟数据',updated:'更新于',used:'已用',total:'总计',cores:'个逻辑核心',paused:'已暂停刷新',boot:'启动时间',normal:'正常',check:'偏高',high:'较高',demo_collection:'浏览器模拟 · 未连接真实监控'}
};
let lang='en', paused=false, metric='cpu', last=null, loading=false;
try{lang=localStorage.getItem('server_lens_language')==='zh'?'zh':'en';}catch{}
const t=key=>copy[lang][key]||key;
const number=(v,d=1)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(d):'—';
const bytes=v=>typeof v==='number'&&Number.isFinite(v)?(v/1073741824).toFixed(1)+' GiB':'—';
const timeLabel=v=>new Date(v).toLocaleTimeString(lang==='zh'?'zh-CN':'en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
function language(){
 document.documentElement.lang=lang==='zh'?'zh-CN':'en';$('language').value=lang;
 document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=t(el.dataset.i18n);});
 $('source-label').textContent=demo?'SIMULATED / DEMO':'LOCAL / PROMETHEUS';
 $('pause').textContent=t(paused?'resume':'pause');
 if(last)render(last);
}
function sample(){
 const end=Math.floor(Date.now()/1000),span={'1h':3600,'6h':21600,'24h':86400}[$('range').value];
 const history={cpu:[],memory:[],disk:[]};
 for(let i=0;i<=60;i++){
  const at=end-span+span*i/60;
  history.cpu.push([at,Math.max(3,15+7*Math.sin(i*.23)+4*Math.sin(i*.69))]);
  history.memory.push([at,34+2*Math.sin(i*.11)]);history.disk.push([at,41.2+i*.004]);
 }
 const memoryPercent=history.memory.at(-1)[1],diskPercent=history.disk.at(-1)[1];
 return {source:'demo',status:'ready',collected_at:new Date().toISOString(),sample_age_seconds:0,cpu:{percent:history.cpu.at(-1)[1],cores:4},memory:{total_bytes:8*1073741824,available_bytes:8*1073741824*(1-memoryPercent/100),percent:memoryPercent},disk:{total_bytes:100*1073741824,available_bytes:100*1073741824*(1-diskPercent/100),percent:diskPercent},uptime_seconds:12*86400+7*3600+34*60,history};
}
function graph(){
 const points=last?.history?.[metric]||[];
 const valid=points.filter(p=>Number.isFinite(p[0])&&Number.isFinite(p[1]));
 $('chart-empty').hidden=valid.length>=2;
 if(valid.length<2){$('line').setAttribute('d','');$('area').setAttribute('d','');$('chart-start').textContent='—';return;}
 const start=points[0][0],end=points.at(-1)[0],duration=Math.max(1,end-start);
 let path='',segment=[],areas=[];
 const close=()=>{if(segment.length>1)areas.push('M'+segment[0][0]+',215 L'+segment.map(p=>p.join(',')).join(' L')+' L'+segment.at(-1)[0]+',215 Z');segment=[];};
 points.forEach(([at,value])=>{
  if(!Number.isFinite(value)){close();return;}
  const xy=[Number(((at-start)/duration*1000).toFixed(2)),Number((215-Math.max(0,Math.min(100,value))*2).toFixed(2))];
  path+=(segment.length?' L':' M')+xy.join(',');segment.push(xy);
 });close();
 $('line').setAttribute('d',path);$('area').setAttribute('d',areas.join(' '));
 $('chart-start').textContent=timeLabel(start*1000);
 $('chart').setAttribute('aria-label',`${t(metric==='cpu'?'cpu':metric)}: ${number(valid.at(-1)[1])}%`);
}
function render(data){
 last=data;
 const age=(Date.now()-new Date(data.collected_at).getTime())/1000;
 const stale=!Number.isFinite(age)||age>90||(data.sample_age_seconds??Infinity)>90;
 const status=stale?'unavailable':data.status;
 $('health').classList.toggle('warning',paused||(!demo&&status!=='ready'));
 $('health').lastElementChild.textContent=t(paused?'paused':demo?'simulated':status);
 $('updated').textContent=(paused?t('paused')+' · ':'')+t('updated')+' '+timeLabel(data.collected_at);
 const unavailable=!demo&&status==='unavailable';
 for(const key of ['cpu','memory','disk']){
  const value=unavailable?null:data[key]?.percent;
  $(key+'-value').textContent=number(value);
  $(key+'-meter').style.width=Number.isFinite(value)?Math.max(0,Math.min(100,value))+'%':'0%';
 }
 const cpu=data.cpu?.percent;
 $('cpu-badge').textContent=unavailable||!Number.isFinite(cpu)?'—':t(cpu>=95?'high':cpu>=80?'check':'normal');
 $('cpu-detail').textContent=unavailable?'—':number(data.cpu?.cores,0)+' '+t('cores');
 for(const key of ['memory','disk']){
  const item=data[key]||{};
  $(key+'-detail').textContent=unavailable?'—':bytes(item.total_bytes!==null&&item.available_bytes!==null?item.total_bytes-item.available_bytes:null)+' '+t('used')+' / '+bytes(item.total_bytes);
  $(key+'-available').textContent=unavailable?'—':bytes(item.available_bytes);
 }
 const seconds=data.uptime_seconds;
 $('uptime-value').textContent=unavailable||!Number.isFinite(seconds)?'—':Math.floor(seconds/86400)+'d '+Math.floor(seconds%86400/3600)+'h';
 $('uptime-detail').textContent=unavailable||!Number.isFinite(seconds)?'—':Math.floor(seconds%3600/60)+'m · '+(demo?t('simulated'):t('boot')+' '+new Date(Date.now()-seconds*1000).toLocaleDateString(lang==='zh'?'zh-CN':'en-GB'));
 $('collection-value').textContent=t(demo?'demo_collection':'collection_value');graph();
}
async function refresh(){
 if(loading)return;loading=true;$('refresh').disabled=true;
 try{
  if(demo)render(sample());
  else{
   const response=await fetch('api/summary?range='+encodeURIComponent($('range').value),{cache:'no-store',signal:AbortSignal.timeout(18000)});
   if(!response.ok)throw new Error('metrics unavailable');
   const data=await response.json();if(data.source!=='prometheus')throw new Error('unexpected source');render(data);
  }
 }catch{
  if(last)render({...last,status:'unavailable'});
  else render({status:'unavailable',source:'prometheus',collected_at:new Date().toISOString(),sample_age_seconds:null,cpu:{},memory:{},disk:{},history:{}});
 }finally{loading=false;$('refresh').disabled=false;}
}
$('demo-banner').hidden=!demo;
$('language').addEventListener('change',()=>{lang=$('language').value;try{localStorage.setItem('server_lens_language',lang);}catch{}language();});
$('pause').addEventListener('click',()=>{paused=!paused;$('pause').setAttribute('aria-pressed',String(paused));language();if(!paused)refresh();});
$('refresh').addEventListener('click',refresh);$('range').addEventListener('change',refresh);
document.querySelectorAll('[data-metric]').forEach(button=>button.addEventListener('click',()=>{metric=button.dataset.metric;document.querySelectorAll('[data-metric]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));graph();}));
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!paused)refresh();});
language();refresh();setInterval(()=>{if(!paused&&!document.hidden)refresh();else if(last)render(last);},30000);
})();
