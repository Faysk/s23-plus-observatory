(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '—').replace(/[&<>"']/g, (x) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const fmt = (v, dec=1) => (typeof v === 'number' && Number.isFinite(v)) ? v.toLocaleString('pt-BR',{maximumFractionDigits:dec,minimumFractionDigits:dec}) : 'Indisponível';
  const dateFmt = (s) => { const d=new Date(s); return Number.isNaN(d.getTime())?'—':d.toLocaleString('pt-BR'); };
  const units = {cpu:'%',memory:'%',battery:'%',temp:'°C',rx:'Mb/s',tx:'Mb/s',storage:'%'};
  const title = {overview:'Visão geral',performance:'Desempenho',battery:'Bateria e energia',network:'Rede',storage:'Armazenamento',system:'Sistema e fontes'};
  const description = {overview:'Saúde e desempenho do seu dispositivo em um só lugar.',performance:'Uso de CPU e memória em amostras reais.',battery:'Capacidade e temperatura da bateria.',network:'Tráfego de rede, quando acessível sem root.',storage:'Uso do volume acessível pelo Termux.',system:'Estado da coleta, serviços e disponibilidade das fontes.'};
  const labels={cpu:'CPU',memory:'Memória',battery:'Bateria',temp:'Temperatura',rx:'Recebimento',tx:'Envio',storage:'Armazenamento'};
  const ranges=['1h','6h','12h','24h','7d','30d','90d'];
  const s={page:'overview',range:'24h',snapshot:null,history:new Map(),requestId:0,lastError:null,paused:false};
  try{s.range=localStorage.getItem('s23_range')||'24h'; if(!ranges.includes(s.range))s.range='24h'; if(localStorage.getItem('s23_theme')==='light')document.body.classList.add('light');}catch{}
  const chartMetricKeys={overview:['cpu','battery'],performance:['cpu','memory'],battery:['battery','temp'],network:['rx','tx'],storage:['storage'],system:[]};
  function pct(v){return v==null?'Indisponível':fmt(v)+'%';}
  function metricCard(label,value,unit,meta,icon,bar=null){
    const available=value!=null && Number.isFinite(Number(value));
    return `<article class="card"><div class="metric-label"><span>${esc(label)}</span><span class="metric-icon" aria-hidden="true">${icon}</span></div><div class="metric-value ${available?'':'missing'}">${available?fmt(Number(value)):'Indisponível'} ${available?`<small>${esc(unit)}</small>`:''}</div><div class="metric-meta">${esc(meta)}</div><progress class="progress" max="100" value="${bar==null?0:Math.max(0,Math.min(100,bar))}" aria-hidden="true"></progress></article>`;
  }
  function groupHead(text,more=''){return `<div class="section-title"><h2>${esc(text)}</h2><small>${esc(more)}</small></div>`;}
  function row(label,value){return `<div class="row-data"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;}
  function box(heading,content){return `<article class="card"><h3>${esc(heading)}</h3>${content}</article>`;}
  function chartShell(metric){return `<div class="card chart-card"><div class="chart-head"><div><h3>${esc(labels[metric])}</h3><p>Histórico real · ${esc(s.range)}</p></div><div class="last-value" id="last-${metric}">—</div></div><div class="chart" id="plot-${metric}"><div class="chart-empty">Carregando histórico…</div></div></div>`;}
  function picker(){return `<div class="range-picker" aria-label="Período do histórico">${ranges.map(r=>`<button type="button" data-range="${r}" class="${r===s.range?'selected':''}" aria-pressed="${r===s.range}">${r}</button>`).join('')}</div>`;}
  function charts(){const keys=chartMetricKeys[s.page];return keys.length?`${groupHead('Histórico de métricas')}<div class="section-title chart-toolbar"><small>Sem interpolação ou valores simulados</small>${picker()}</div><div class="chart-grid">${keys.map(chartShell).join('')}</div>`:'';}
  function render(){
    const d=s.snapshot, root=$('#content-region');
    if(!d){root.innerHTML='<div class="empty">Sem amostras reais. Verifique o coletor no Termux.</div>';return;}
    let html='';
    const c=d.cpu||{},m=d.memory||{},b=d.battery||{},n=d.network||{},disk=d.storage?.[0]||{};
    const memoryPct=m.totalMB>0&&m.usedMB!=null?m.usedMB/m.totalMB*100:null;
    if(s.page==='overview'||s.page==='performance'){
      html+=`<div class="stats-grid">${metricCard('CPU',c.usagePercent,'%','Uso global','⌁',c.usagePercent)}${metricCard('Memória',memoryPct,'%','RAM utilizada','▤',memoryPct)}${metricCard('Bateria',b.levelPercent,'%','Carga atual','⚡',b.levelPercent)}${metricCard('Armazenamento',disk.usedPercent,'%','Volume do Termux','◫',disk.usedPercent)}</div>`;
    } else if(s.page==='battery'){
      html+=`<div class="stats-grid">${metricCard('Bateria',b.levelPercent,'%','Capacidade atual','⚡',b.levelPercent)}${metricCard('Temperatura',b.temperatureC,'°C','Sensor da bateria','♨')}${metricCard('Memória',memoryPct,'%','RAM usada','▤',memoryPct)}${metricCard('Armazenamento',disk.usedPercent,'%','Volume do Termux','◫',disk.usedPercent)}</div>`;
    } else if(s.page==='network'){
      html+=`<div class="stats-grid">${metricCard('Download',n.rxMbps,'Mb/s','Taxa observada, não velocidade do plano','↓')}${metricCard('Upload',n.txMbps,'Mb/s','Taxa observada, não velocidade do plano','↑')}</div>`;
    } else if(s.page==='storage'){
      html+=`<div class="stats-grid">${metricCard('Ocupação',disk.usedPercent,'%','Volume do Termux','◫',disk.usedPercent)}${metricCard('Utilizado',disk.usedGB,'GB','Decimal (1 GB = 10⁹ bytes)','▣')}${metricCard('Disponível',disk.availableGB,'GB','Espaço disponível ao processo','◉')}</div>`;
    }
    html+=charts();
    if(s.page==='overview'||s.page==='system'){
      html+=groupHead('Dispositivo e serviços');
      html+=`<div class="detail-grid">${box('Identificação',row('Modelo',d.device?.model||'Indisponível')+row('Sistema',d.device?.os||'Indisponível')+row('Arquitetura',d.device?.architecture||'Indisponível')+row('Origem','Termux / Android'))}${box('Estado da coleta',row('Última amostra',dateFmt(d.timestamp))+row('SSH · porta 8022',d.services?.find(x=>x.id==='ssh')?.status||'Indisponível')+row('Fonte bateria',b.source||'Indisponível')+row('CPU',d.diagnostics?.cpuSource||'Indisponível'))}</div>`;
    }
    if(s.page==='performance'){
      html+=groupHead('Memória do sistema');html+=`<div class="detail-grid">${box('RAM',row('Total',m.totalMB==null?'Indisponível':fmt(m.totalMB)+' MB')+row('Usada',m.usedMB==null?'Indisponível':fmt(m.usedMB)+' MB')+row('Disponível',m.availableMB==null?'Indisponível':fmt(m.availableMB)+' MB'))}${box('CPU',row('Uso global',pct(c.usagePercent))+row('Núcleos com leitura',Array.isArray(c.coresPercent)?c.coresPercent.filter(x=>x!=null).length+' de '+c.coresPercent.length:'Indisponível')+row('Temperatura da CPU','Não validada / indisponível'))}</div>`;
    }
    if(s.page==='battery'){
      html+=groupHead('Detalhes da bateria');html+=`<div class="detail-grid">${box('Energia',row('Estado',b.status||'Indisponível')+row('Alimentação',b.plugged||'Indisponível')+row('Saúde informada',b.health||'Indisponível'))}${box('Sensor',row('Fonte',b.source||'Indisponível')+row('Temperatura',b.temperatureC==null?'Indisponível':fmt(b.temperatureC)+' °C')+row('Nível',pct(b.levelPercent)))}</div>`;
    }
    if(s.page==='network'){
      html+=groupHead('Interface');html+=`<div class="detail-grid">${box('Tráfego',row('Interface',n.interface||'Indisponível')+row('Contadores',d.diagnostics?.networkSource||'Indisponível')+row('Recebido',n.rxMbps==null?'Indisponível':fmt(n.rxMbps,4)+' Mb/s')+row('Enviado',n.txMbps==null?'Indisponível':fmt(n.txMbps,4)+' Mb/s'))}${box('Privacidade',row('SSID / rede Wi-Fi','Não coletado')+row('Localização','Não coletada')+row('Endereço IP','Não divulgado pela API'))}</div>`;
    }
    if(s.page==='storage'){
      html+=groupHead('Filesystem');html+=`<div class="detail-grid">${box('Volume acessível',row('Volume',disk.label||'Indisponível')+row('Total',disk.totalGB==null?'Indisponível':fmt(disk.totalGB,2)+' GB')+row('Usado',disk.usedGB==null?'Indisponível':fmt(disk.usedGB,2)+' GB')+row('Disponível',disk.availableGB==null?'Indisponível':fmt(disk.availableGB,2)+' GB'))}${box('Interpretação',row('Escopo','Filesystem do Termux')+row('Unidades','GB decimais')+row('Leitura do microSD','Não incluída'))}</div>`;
    }
    if(s.page==='system'){
      html+=groupHead('Disponibilidade das fontes');
      const availability=Object.entries(d.availability||{}).map(([k,v])=>row(k,v?'Disponível':'Indisponível')).join('');
      html+=`<div class="detail-grid">${box('Sensores',availability)}${box('Diagnóstico',row('CPU',d.diagnostics?.cpuSource||'Indisponível')+row('Rede',d.diagnostics?.networkSource||'Indisponível')+row('Bateria',d.diagnostics?.batterySource||'Indisponível')+row('Notas','Sem root; indisponível ≠ 0'))}</div>`;
    }
    root.innerHTML=html;
    loadCharts();
  }
  function renderChart(metric, points){
    const parent=$('#plot-'+metric), last=$('#last-'+metric);if(!parent||!last)return;
    const vals=points.filter(p=>typeof p.value==='number' && Number.isFinite(p.value) && Number.isFinite(p.time));
    last.textContent=vals.length?`${fmt(vals[vals.length-1].value,2)} ${units[metric]}`:'—';
    if(!vals.length){parent.innerHTML='<div class="chart-empty">Sem amostras para este período</div>';return;}
    const W=600,H=185,L=38,R=12,T=15,B=29;
    const bottom=H-B,plotH=bottom-T,plotW=W-L-R;
    const times=vals.map(p=>p.time),v=vals.map(p=>p.value);
    let min=Math.min(...v),max=Math.max(...v);
    if(min===max){min-=Math.max(1,Math.abs(min)*.04);max+=Math.max(1,Math.abs(max)*.04);}
    const pad=(max-min)*.12;min-=pad;max+=pad;
    const domainStart=Date.now()-({ '1h':3600,'6h':21600,'12h':43200,'24h':86400,'7d':604800,'30d':2592000,'90d':7776000}[s.range])*1000;
    const domainEnd=Date.now();
    const x=t=>L+(Math.max(domainStart,Math.min(domainEnd,t))-domainStart)/(domainEnd-domainStart)*plotW;
    const y=n=>T+(max-n)/(max-min)*plotH;
    const expected=(domainEnd-domainStart)/240;
    const segments=[];let segment=[];
    vals.forEach((p,i)=>{if(i&&p.time-vals[i-1].time>Math.max(90000,expected*5)){if(segment.length)segments.push(segment);segment=[];}segment.push(p);});
    if(segment.length)segments.push(segment);
    let paths=segments.map(seg=>'<path class="line" d="'+seg.map((p,i)=>(i?'L':'M')+x(p.time).toFixed(2)+' '+y(p.value).toFixed(2)).join(' ')+'"/>').join('');
    const lines=[0,.5,1].map(z=>{const yy=T+z*plotH;return `<line class="gridline" x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}"/><text class="axis" x="${L-5}" y="${yy+3}" text-anchor="end">${fmt(max-z*(max-min),1)}</text>`}).join('');
    const timeLabel=(t)=>new Date(t).toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit'});
    parent.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Histórico ${esc(labels[metric])}, ${vals.length} amostras agregadas">${lines}${paths}<text class="axis" x="${L}" y="${H-7}">${timeLabel(domainStart)}</text><text class="axis" x="${W-R}" y="${H-7}" text-anchor="end">${timeLabel(domainEnd)}</text></svg>`;
  }
  async function loadCharts(){
    const generation=++s.requestId;
    const requested=s.range;
    const keys=chartMetricKeys[s.page];
    await Promise.all(keys.map(async metric=>{
      const key=metric+':'+requested;
      const cached=s.history.get(key);
      if(cached&&Date.now()-cached.ts<60000){if(generation===s.requestId)renderChart(metric,cached.points);return;}
      try{
        const res=await fetch(`/api/host/history?metric=${encodeURIComponent(metric)}&range=${encodeURIComponent(requested)}`,{cache:'no-store'});
        if(!res.ok)throw new Error('HTTP '+res.status);
        const data=await res.json();
        if(!Array.isArray(data.points))throw new Error('Histórico inválido');
        s.history.set(key,{ts:Date.now(),points:data.points});
        if(s.history.size>30)s.history.delete(s.history.keys().next().value);
        if(generation===s.requestId)renderChart(metric,data.points);
      }catch{
        const target=$('#plot-'+metric);
        if(generation===s.requestId&&target)target.innerHTML='<div class="chart-empty">Erro ao carregar histórico</div>';
      }
    }));
  }
  function statusInfo(){
    const stamp=s.snapshot?.timestamp?new Date(s.snapshot.timestamp).getTime():NaN;
    const age=Date.now()-stamp;
    const fresh=Number.isFinite(age)&&age>=-20000&&age<120000;
    const live=$('#live-state'),dot=$('#sidebar-dot');
    live.classList.toggle('ok',fresh); dot.parentElement.classList.toggle('ok',fresh);
    live.innerHTML=`<span class="dot"></span> ${fresh?'DADOS REAIS':s.snapshot?'DADOS ANTIGOS':'AGUARDANDO'}`;
    $('#sidebar-label').textContent=fresh?'Coletor ativo':s.snapshot?'Telemetria antiga':'Aguardando telemetria';
    $('#updated').textContent=s.snapshot?'Última amostra: '+dateFmt(s.snapshot.timestamp):'Sem leituras recebidas';
    const warning=$('#warning');
    warning.hidden=fresh&&!s.lastError;
    warning.textContent=s.lastError?'Não foi possível atualizar. Confira o serviço no Termux.':(!fresh&&s.snapshot?'A última amostra está antiga. Verifique o coletor e as restrições de bateria.':'');
    if(!s.snapshot&&!s.lastError)warning.hidden=true;
  }
  async function refresh(){
    try{
      const res=await fetch('/api/host/snapshot',{cache:'no-store'});
      if(!res.ok)throw new Error('HTTP '+res.status);
      const data=await res.json();
      if(data?.source!=='live'||!data.timestamp)throw new Error('Dados inválidos');
      const changed=!s.snapshot||s.snapshot.timestamp!==data.timestamp;
      s.snapshot=data;s.lastError=null;
      if(changed)render();
    }catch(e){s.lastError=String(e);if(!s.snapshot)$('#content-region').innerHTML='<div class="empty">Sem conexão com o coletor. Confira o comando de inicialização no Termux.</div>';}
    statusInfo();
  }
  $('#nav').addEventListener('click',ev=>{
    const button=ev.target.closest('button[data-page]');if(!button)return;
    s.page=button.dataset.page;$('#nav').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b===button));
    $('#page-title').textContent=title[s.page];$('#crumb-page').textContent=title[s.page];$('#page-description').textContent=description[s.page];
    render();
  });
  $('#content-region').addEventListener('click',ev=>{
    const b=ev.target.closest('button[data-range]');if(!b)return;
    if(!ranges.includes(b.dataset.range))return;
    s.range=b.dataset.range;try{localStorage.setItem('s23_range',s.range);}catch{}render();
  });
  $('#refresh').addEventListener('click',()=>{s.history.clear();refresh();if(s.snapshot)loadCharts();});
  $('#theme-button').addEventListener('click',()=>{document.body.classList.toggle('light');try{localStorage.setItem('s23_theme',document.body.classList.contains('light')?'light':'dark');}catch{}});
  function clock(){ $('#clock').textContent=new Date().toLocaleTimeString('pt-BR');statusInfo(); }
  setInterval(clock,1000);setInterval(()=>{if(!document.hidden)refresh();},15000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  clock();refresh();
})();
