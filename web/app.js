/* S23 Observatory v0.2 — original local-first UI, no external resources. */
(() => {
  'use strict';
  const $=s=>document.querySelector(s);
  const esc=v=>String(v??'—').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const fmt=(v,d=1)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('pt-BR',{maximumFractionDigits:d}):'Sem dados';
  const val=(v,u='',d=1)=>v==null?'Sem dados':fmt(v,d)+(u?' '+u:'');
  const date=t=>new Date(t).toLocaleString('pt-BR');
  const duration=t=>t==null?'Sem dados':`${Math.floor(t/86400)}d ${Math.floor(t%86400/3600)}h ${Math.floor(t%3600/60)}min`;
  const save=(k,v)=>{try{localStorage.setItem('s23_'+k,v);}catch{}};
  const read=(k,f)=>{try{return localStorage.getItem('s23_'+k)??f;}catch{return f;}};
  const ranges={'1h':3600,'6h':21600,'12h':43200,'24h':86400,'7d':604800,'30d':2592000,'90d':7776000};
  const pages={overview:['Visão geral','O estado do Galaxy S23+, dos sensores ao histórico.'],performance:['Desempenho','CPU por núcleo, frequências e memória do sistema.'],battery:['Bateria e energia','Carga, temperatura e tensão com a origem da leitura.'],network:['Rede','Tráfego observado e qualidade do link Wi-Fi são medidas diferentes.'],storage:['Armazenamento','Capacidade e espaço disponível no volume acessível pelo Termux.'],explorer:['Explorar leituras','Catálogo pesquisável: valor, unidade e origem de cada métrica.'],system:['Sistema e fontes','Saúde do coletor, atualização das fontes e persistência local.']};
  const metrics={overview:['cpu','memory','rx','tx'],performance:['cpu','memory','frequency','swap'],battery:['battery','temp','voltage'],network:['rx','tx','signal','linkRx'],storage:['storage','storageFree'],system:['processCpu','processMemory','collection'],explorer:[]};
  const labels={cpu:'CPU global',memory:'RAM utilizada',rx:'Recebimento',tx:'Envio',battery:'Nível da bateria',temp:'Temperatura da bateria',voltage:'Tensão',frequency:'Frequência observada',swap:'Swap utilizada',signal:'Sinal Wi-Fi',linkRx:'Link Wi-Fi RX',storage:'Volume ocupado',storageFree:'Espaço disponível',processCpu:'CPU do coletor',processMemory:'Memória do coletor',collection:'Tempo de coleta'};
  const units={cpu:'%',memory:'%',rx:'Mb/s',tx:'Mb/s',battery:'%',temp:'°C',voltage:'mV',frequency:'MHz',swap:'MiB',signal:'dBm',linkRx:'Mb/s',storage:'%',storageFree:'GB',processCpu:'%',processMemory:'MiB',collection:'ms'};
  const s={page:'overview',range:read('range','1h'),fit:read('fit','true')!=='false',snapshot:null,catalog:null,paused:false,error:null,query:'',group:'all',limit:24,generation:0};
  if(!ranges[s.range])s.range='1h';
  const cache=new Map(),flights=new Map();let refreshing=false;
  if(read('theme','dark')==='light')document.body.classList.add('light');
  const translations={FULL:'Carga completa',CHARGING:'Carregando',DISCHARGING:'Descarregando',NOT_CHARGING:'Sem carregar',GOOD:'Boa (Android)',USB:'USB',AC:'Tomada',WIRELESS:'Sem fio',UNPLUGGED:'Bateria',UNKNOWN:'Não informado'};
  const translated=v=>translations[v]||v||'Sem dados';
  const row=(name,v)=>`<div class="row-data"><span>${esc(name)}</span><strong>${esc(v)}</strong></div>`;
  const box=(name,body)=>`<article class="card detail-card"><h3>${esc(name)}</h3>${body}</article>`;
  const group=(name,body,note='')=>`<div class="section-title"><h2>${esc(name)}</h2><small>${esc(note)}</small></div>${body}`;
  function card(name,v,unit,meta,goto,tone='mint',percent=null) {
    return `<button type="button" class="card metric-card tone-${tone}" data-goto="${goto}"><span class="metric-label">${esc(name)}<span aria-hidden="true">↗</span></span><span class="metric-value ${v==null?'missing':''}">${v==null?'Sem dados':esc(fmt(v,unit==='Mb/s'?4:1))}${v==null?'':` <small>${esc(unit)}</small>`}</span><span class="metric-meta">${esc(meta)}</span>${percent==null?'':`<progress class="progress" max="100" value="${Math.max(0,Math.min(100,percent))}" aria-label="${esc(name)}"></progress>`}</button>`;
  }
  function snapshotView() {
    const d=s.snapshot;if(!d)return '<div class="empty">Aguardando uma amostra válida do dispositivo.</div>';
    const c=d.cpu,m=d.memory,b=d.battery,n=d.network,disk=d.storage[0],diag=d.diagnostics||{},mon=d.monitor||{};
    const memPct=m.usedPercent??(m.usedMB!=null&&m.totalMB?m.usedMB/m.totalMB*100:null);
    let html='';
    if(s.page==='overview') {
      html=`<div class="hero-strip"><div><span class="eyebrow">GALAXY S23+</span><strong>${esc(d.device.model)} <span>· ${esc(d.device.os)}</span></strong></div><div><small>Tempo ligado</small><b>${duration(d.device.uptimeSec)}</b></div><div><small>Fontes disponíveis</small><b>${Object.values(d.availability).filter(Boolean).length} / ${Object.keys(d.availability).length}</b></div><div><small>Cadência de coleta</small><b>${diag.sampleIntervalSec??30} segundos</b></div></div>`;
      html+='<div class="stats-grid">'+card('CPU global',c.usagePercent,'%','Janela '+val(diag.cpuWindowSec,'s'), 'performance','mint',c.usagePercent)+card('Memória RAM',memPct,'%',val(m.availableMB,'MiB')+' disponíveis','performance','blue',memPct)+card('Bateria',b.levelPercent,'%',translated(b.status),'battery','violet',b.levelPercent)+card('Temperatura',b.temperatureC,'°C','Sensor da bateria','battery','amber')+card('Recebimento',n.rxMbps,'Mb/s','Interface '+(n.interface??'indisponível'),'network','blue')+card('Armazenamento',disk.usedPercent,'%',val(disk.availableGB,'GB')+' disponíveis','storage','mint',disk.usedPercent)+'</div>';
      const notices=[];
      if(memPct>=85)notices.push('RAM acima de 85% nesta amostra. O Android gerencia cache e processos em segundo plano.');
      if(b.temperatureC>=40)notices.push('Bateria a '+val(b.temperatureC,'°C')+'. Referência de atenção do painel: 40 °C.');
      if(disk.usedPercent>=90)notices.push('Volume com 90% ou mais de ocupação.');
      if(!d.availability.cpu)notices.push('CPU sem amostra válida: confira o agente Android na seção Sistema.');
      if(notices.length)html+='<div class="observations">'+notices.map(x=>'<p>◌ '+esc(x)+'</p>').join('')+'</div>';
    }
    if(s.page==='performance') {
      html='<div class="stats-grid">'+card('CPU global',c.usagePercent,'%','Delta dos contadores do sistema','performance','mint',c.usagePercent)+card('Frequência observada',c.frequencyMHz,'MHz','Maior leitura atual entre os núcleos','performance','blue')+card('RAM disponível',m.availableMB,'MiB','MemAvailable do kernel','performance','violet')+card('Swap em uso',m.swapUsedMB,'MiB','Capacidade '+val(m.swapMB,'MiB'),'performance','amber')+'</div>';
      html+=group('Atividade por núcleo',`<div class="core-grid">${Array.from({length:Math.max(8,c.coresPercent?.length||0)},(_,i)=>`<article class="core-card"><div><span>CPU ${i}</span><strong>${val(c.coresPercent?.[i],'%')}</strong></div>${c.coresPercent?.[i]==null?'<small>Sem leitura do núcleo</small>':`<progress max="100" value="${c.coresPercent[i]}" aria-label="CPU ${i}"></progress>`}<small>${val(c.coresFrequencyMHz?.[i],'MHz',0)}</small></article>`).join('')}</div>`,'CPU do chipset: temperatura não homologada');
      html+=group('Memória e carga',`<div class="detail-grid">${box('RAM do Android',row('Total',val(m.totalMB,'MiB'))+row('Usada',val(m.usedMB,'MiB'))+row('Disponível',val(m.availableMB,'MiB'))+row('Cache',val(m.cachedMB,'MiB'))+row('Buffers',val(m.buffersMB,'MiB'))+row('Slab',val(m.slabMB,'MiB')))}${box('Carga e memória virtual',row('Carga · 1 minuto',val(c.loadAverage?.[0]))+row('Carga · 5 minutos',val(c.loadAverage?.[1]))+row('Carga · 15 minutos',val(c.loadAverage?.[2]))+row('Swap total',val(m.swapMB,'MiB'))+row('Swap usada',val(m.swapUsedMB,'MiB'))+row('Swap livre',val(m.swapFreeMB,'MiB')))}</div>`,'Cache, slab e RAM usada podem se sobrepor; não somar.');
    }
    if(s.page==='battery')html='<div class="stats-grid">'+card('Carga',b.levelPercent,'%',translated(b.status),'battery','violet',b.levelPercent)+card('Temperatura',b.temperatureC,'°C','Sensor da bateria','battery','amber')+card('Tensão',b.voltageMV,'mV','Reportada pelo serviço Android','battery','blue')+'</div>'+group('Estado de energia',`<div class="detail-grid">${box('Bateria',row('Estado',translated(b.status))+row('Alimentação',translated(b.plugged))+row('Saúde informada',translated(b.health)))}${box('Origem e interpretação',row('Fonte',b.source||'Sem dados')+row('Corrente / potência','Sem fonte validada')+row('Estimativa de autonomia','Não calculada'))}</div>`);
    if(s.page==='network')html='<div class="stats-grid">'+card('Recebimento',n.rxMbps,'Mb/s','Tráfego observado','network','blue')+card('Envio',n.txMbps,'Mb/s','Tráfego observado','network','mint')+card('Sinal Wi-Fi',n.signalDbm,'dBm','Potência recebida pelo S23','network','violet')+card('Link RX',n.rxLinkMbps,'Mb/s','Taxa física informada; não é consumo','network','amber')+'</div>'+group('Interface e contadores',`<div class="detail-grid">${box('Wi-Fi',row('Interface',n.interface||'Sem dados')+row('Frequência do canal',val(n.frequencyMHz,'MHz',0))+row('Link RX',val(n.rxLinkMbps,'Mb/s'))+row('Link TX',val(n.txLinkMbps,'Mb/s'))+row('Fonte',diag.networkSource||'Sem dados'))}${box('Acumulados da interface',row('Recebidos',val(n.rxBytes==null?null:n.rxBytes/1e9,'GB',3))+row('Enviados',val(n.txBytes==null?null:n.txBytes/1e9,'GB',3))+row('Pacotes RX / TX',`${val(n.rxPackets,'',0)} / ${val(n.txPackets,'',0)}`)+row('Erros RX / TX',`${val(n.rxErrors,'',0)} / ${val(n.txErrors,'',0)}`)+row('Descartes RX / TX',`${val(n.rxDrops,'',0)} / ${val(n.txDrops,'',0)}`))}</div>`,'Acumulados desde a criação/reset da interface. Não representam um período do gráfico.');
    if(s.page==='storage')html='<div class="stats-grid">'+card('Ocupação',disk.usedPercent,'%','Volume acessível pelo Termux','storage','mint',disk.usedPercent)+card('Utilizado',disk.usedGB,'GB','Decimal · 1 GB = 10⁹ bytes','storage','violet')+card('Disponível',disk.availableGB,'GB','Espaço disponível ao usuário','storage','blue')+card('Capacidade',disk.totalGB,'GB','Volume completo, incluindo Android','storage','amber')+'</div>'+group('Escopo do armazenamento',`<div class="detail-grid">${box('Volume',row('Nome',disk.label)+row('Escopo','Filesystem do Termux / dados Android')+row('Outros aplicativos','Sem leitura de arquivos pessoais'))}${box('Histórico local',row('Retenção',val(s.catalog?.storage?.retentionDays,'dias',0))+row('Snapshots completos',val(s.catalog?.storage?.snapshots,'',0))+row('Formato','SQLite local; agregados preservam os extremos'))}</div>`);
    if(s.page==='system')html='<div class="stats-grid">'+card('CPU do coletor',mon.cpuPercent,'%','100% equivale a um núcleo','system','mint')+card('RAM do coletor',mon.rssMB,'MiB','Memória residente atual','system','blue')+card('Tempo de coleta',mon.collectionMs,'ms','Antes da gravação no SQLite','system','violet')+'</div>'+group('Dispositivo e coleta',`<div class="detail-grid">${box('Identificação',row('Modelo',d.device.model)+row('Sistema',d.device.os)+row('Arquitetura',d.device.architecture)+row('Tempo ligado',duration(d.device.uptimeSec))+row('SSH · porta 8022',d.services?.[0]?.status||'Sem dados'))}${box('Fontes e atualização',row('CPU',diag.cpuSource||'Sem dados')+row('Rede',diag.networkSource||'Sem dados')+row('Bateria',diag.batterySource||'Sem dados')+row('Idade da amostra ADB',val(diag.agentAgeSeconds,'s'))+row('Janela de CPU',val(diag.cpuWindowSec,'s',2))+row('Erro do coletor',diag.lastError||'Nenhum informado'))}${box('Persistência',row('Snapshots completos',val(s.catalog?.storage?.snapshots,'',0))+row('Retenção',val(s.catalog?.storage?.retentionDays,'dias',0))+row('Primeiro snapshot completo',s.catalog?.storage?.firstSample?date(s.catalog.storage.firstSample*1000):'Sem dados'))}${box('Limites das fontes',row('Agente ADB','Expira após 150 s; reiniciar após reboot do Android')+row('Temperatura da CPU','Não homologada')+row('Corrente / saúde física','Sem medição validada')+row('Dados pessoais','Sem contatos, localização ou conteúdo de arquivos'))}</div>`);
    return html;
  }
  function explorerRows() {
    const defs=Object.entries(s.catalog?.metrics||{});
    const filtered=defs.filter(([key,d])=>(s.group==='all'||d.group===s.group)&&`${key} ${d.label} ${d.source}`.toLocaleLowerCase('pt-BR').includes(s.query.toLocaleLowerCase('pt-BR')));
    const node=$('#explorer-body');if(!node)return;
    node.innerHTML=filtered.slice(0,s.limit).map(([key,d])=>`<tr><td><strong>${esc(d.label)}</strong><small>${esc(key)}</small></td><td class="numeric">${esc(val(d.value,d.unit,d.unit==='Mb/s'?4:1))}</td><td><span class="badge ${d.value==null?'missing':'available'}">${d.value==null?'Sem dados':'Disponível'}</span></td><td>${esc(d.source)}</td></tr>`).join('')||'<tr><td colspan="4">Nenhuma leitura encontrada.</td></tr>';
    $('#explorer-count').textContent=`${Math.min(s.limit,filtered.length)} de ${filtered.length} leituras · atualização por amostra`;
    $('#load-more').hidden=s.limit>=filtered.length;
  }
  function chartShell() {
    if(!metrics[s.page].length)return '';
    return `<div class="section-title"><h2>Histórico de métricas</h2><div class="range-picker" aria-label="Período do histórico">${Object.keys(ranges).map(r=>`<button type="button" data-range="${r}" aria-pressed="${r===s.range}">${r}</button>`).join('')}</div></div><div class="chart-toolbar"><span>Linha: média · faixa: mínimo e máximo · lacunas preservadas</span><label><input id="fit-samples" type="checkbox" ${s.fit?'checked':''}> Ajustar às amostras disponíveis</label></div><div class="chart-grid">${metrics[s.page].map(key=>`<article class="card chart-card" data-metric="${key}"><div class="chart-head"><div><h3>${esc(labels[key])}</h3><p class="chart-period">${s.range} · ${s.fit?'janela das amostras':'período completo'}</p></div><button class="text-button" type="button" disabled data-csv="${key}" aria-label="Exportar CSV agregado de ${esc(labels[key])}">↓ CSV</button></div><div class="chart" id="plot-${key}" aria-busy="true"><div class="chart-skeleton" role="status"><span class="skeleton-axis"></span><span class="skeleton-line"></span><span class="skeleton-bar"></span><b>Carregando histórico…</b></div></div><div class="chart-stats" id="stats-${key}"></div><div class="history-message" id="message-${key}" role="status"></div></article>`).join('')}</div>`;
  }
  function explorerShell() {
    return `<div class="card explorer-toolbar"><label>Buscar leitura<input id="reading-search" type="search" placeholder="CPU, memória, fonte…" value="${esc(s.query)}"></label><label>Grupo<select id="reading-group"><option value="all">Todos os grupos</option>${[...new Set(Object.values(s.catalog?.metrics||{}).map(d=>d.group))].map(g=>`<option ${s.group===g?'selected':''}>${esc(g)}</option>`).join('')}</select></label><span id="explorer-count"></span></div><div class="card table-wrap"><table><caption class="sr-only">Catálogo de métricas e fontes do S23</caption><thead><tr><th>Leitura</th><th>Valor atual</th><th>Estado</th><th>Fonte / interpretação</th></tr></thead><tbody id="explorer-body"></tbody></table><button id="load-more" type="button" class="button">Carregar mais</button></div>`;
  }
  function mount() {
    window.S23Charts.destroy($('#content-region'));
    s.generation++;
    for(const [key,f] of flights)if(!metrics[s.page].some(m=>key===`${m}:${s.range}`)){f.controller.abort();flights.delete(key);}
    $('#content-region').innerHTML=s.page==='explorer'?explorerShell():`<div id="snapshot-region">${snapshotView()}</div><div id="charts-region">${chartShell()}</div>`;
    $('#content-region').classList.remove('page-enter');
    requestAnimationFrame(()=>$('#content-region').classList.add('page-enter'));
    explorerRows();loadCharts();
  }
  function drawHistory(key,data,old=false) {
    const host=$('#plot-'+key);if(!host)return;
    if(host.dataset.version===`${s.range}:${s.fit}:${data.version}`){if(old)$('#message-'+key).textContent='Histórico anterior desta faixa; falha ao atualizar.';return;}
    if(host.contains(document.activeElement))return;
    host.dataset.version=`${s.range}:${s.fit}:${data.version}`;host.setAttribute('aria-busy','false');
    window.S23Charts.draw(host,data,{label:labels[key],unit:units[key],start:Date.now()-ranges[s.range]*1000,end:Date.now(),fit:s.fit,percent:['cpu','memory','battery','storage'].includes(key),interval:data.sampleIntervalSec||30});
    host.closest('.chart-card').querySelector('[data-csv]').disabled=!data.points.length;
    const q=data.summary||{};
    $('#stats-'+key).innerHTML=[['Mínimo',q.min],['Média',q.mean],['Máximo',q.max]].map(([name,v])=>`<span>${name}<strong>${esc(val(v,units[key],2))}</strong></span>`).join('')+`<span>Amostras<strong>${q.count??0}</strong></span>`;
    $('#message-'+key).textContent=old?'Histórico anterior desta faixa; falha ao atualizar.':q.count?`${date(q.firstTime)} → ${date(q.lastTime)}`:'Sem amostras para este período.';
  }
  async function history(key) {
    const id=`${key}:${s.range}`,cached=cache.get(id);
    if(cached&&Date.now()-cached.saved<30000)return cached.data;
    if(flights.has(id))return flights.get(id).promise;
    const chart=$('#plot-'+key)?.closest('.chart-card');
    chart?.classList.add('is-loading');
    const controller=new AbortController();
    const promise=(async()=>{
      const r=await fetch(`/s23/api/host/history?metric=${encodeURIComponent(key)}&range=${encodeURIComponent(s.range)}`,{cache:'no-store',signal:controller.signal});
      if(!r.ok)throw new Error('Histórico indisponível');
      const data=await r.json();if(!Array.isArray(data.points))throw new Error('Histórico inválido');
      data.version=Date.now();cache.set(id,{saved:Date.now(),data});
      while(cache.size>28)cache.delete(cache.keys().next().value);
      return data;
    })().finally(()=>{if(flights.get(id)?.controller===controller)flights.delete(id);chart?.classList.remove('is-loading');});
    flights.set(id,{controller,promise});return promise;
  }
  async function loadCharts() {
    if(s.paused||document.hidden)return;
    const generation=s.generation,range=s.range;
    await Promise.all(metrics[s.page].map(async key=>{
      try {const data=await history(key);if(generation===s.generation&&range===s.range)drawHistory(key,data);}
      catch(error){if(error.name==='AbortError'||generation!==s.generation)return;
        const old=cache.get(`${key}:${range}`);if(old)drawHistory(key,old.data,true);
        else {const node=$('#plot-'+key);if(node){node.setAttribute('aria-busy','false');node.innerHTML='<div class="chart-empty">Histórico indisponível. Use Atualizar para tentar novamente.</div>';}}}
    }));
  }
  function status() {
    const age=s.snapshot?Math.max(0,(Date.now()-Date.parse(s.snapshot.timestamp))/1000):null;
    const fresh=age!=null&&age<Math.max(75,(s.snapshot?.diagnostics?.sampleIntervalSec||30)*2.5)&&!s.error;
    $('#live-state').classList.toggle('ok',fresh&&!s.paused);
    $('#live-state').innerHTML=`<span class="dot"></span>${s.paused?'VISUALIZAÇÃO PAUSADA':fresh?'DADOS REAIS':s.snapshot?'DADOS ANTIGOS':'AGUARDANDO'}`;
    $('#sidebar-dot').parentElement.classList.toggle('ok',fresh);
    $('#sidebar-label').textContent=s.paused?'Visualização pausada':fresh?'Coletor ativo':'Verificar conexão';
    $('#sample-note').textContent=s.snapshot?`Amostra há ${fmt(age,0)} s · coleta a cada ${s.snapshot.diagnostics?.sampleIntervalSec||30} s`:'Coleta local · sem root';
    $('#updated').textContent=s.snapshot?'Última amostra: '+date(s.snapshot.timestamp):'Sem amostras recebidas';
    const warning=$('#warning');warning.hidden=!s.error&&(fresh||!s.snapshot)&&!s.paused;
    warning.textContent=s.paused?'Somente a visualização está pausada. O dispositivo continua coletando e gravando.':s.error?'Falha ao atualizar. A última leitura recebida foi preservada e pode estar antiga.':'A coleta está desatualizada. Confira o serviço e o agente Android.';
  }
  async function refresh(force=false) {
    if(refreshing||(s.paused&&!force))return;refreshing=true;
    $('#refresh').classList.add('is-refreshing');$('#refresh').setAttribute('aria-busy','true');$('#refresh').disabled=true;
    try {
      const r=await fetch('/s23/api/host/snapshot',{cache:'no-store'});if(!r.ok)throw new Error('Snapshot indisponível');
      const d=await r.json();if(d.source!=='live'||!d.timestamp)throw new Error('Amostra inválida');
      const changed=d.timestamp!==s.snapshot?.timestamp;s.snapshot=d;s.error=null;
      if(changed||!s.catalog) {
        try {const catalogResponse=await fetch('/s23/api/host/catalog',{cache:'no-store'});if(catalogResponse.ok)s.catalog=await catalogResponse.json();}catch{}
        if($('#snapshot-region'))$('#snapshot-region').innerHTML=snapshotView();
        if(s.page==='explorer'){if(!$('#reading-group')?.options.length||$('#reading-group').options.length===1)mount();else explorerRows();}
      }
      await loadCharts();
    }catch(e){s.error=e.message;}finally{refreshing=false;$('#refresh').classList.remove('is-refreshing');$('#refresh').setAttribute('aria-busy','false');$('#refresh').disabled=false;status();}
  }
  function navigate(page) {
    if(!pages[page])page='overview';s.page=page;
    $('#page-title').textContent=pages[page][0];$('#page-description').textContent=pages[page][1];$('#crumb-page').textContent=pages[page][0];
    $('#nav').querySelectorAll('[data-page]').forEach(b=>{b.classList.toggle('active',b.dataset.page===page);b.setAttribute('aria-current',b.dataset.page===page?'page':'false');});
    historyState(page);mount();
  }
  function historyState(page){try{window.history.replaceState(null,'','#'+page);}catch{}}
  function download(name,data,type){const url=URL.createObjectURL(new Blob([data],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  $('#nav').addEventListener('click',event=>{const b=event.target.closest('[data-page]');if(b)navigate(b.dataset.page);});
  $('#content-region').addEventListener('click',event=>{
    const card=event.target.closest('[data-goto]');if(card&&card.dataset.goto!==s.page){navigate(card.dataset.goto);return;}
    const range=event.target.closest('[data-range]');if(range){s.range=range.dataset.range;save('range',s.range);mount();$('#content-region [data-range="'+s.range+'"]').focus();return;}
    const csv=event.target.closest('[data-csv]');if(csv){const data=cache.get(`${csv.dataset.csv}:${s.range}`)?.data;if(!data)return;const header='timestamp_iso,mean,min,max,sample_count,unit\n';const rows=data.points.map(p=>[new Date(p.time).toISOString(),p.value,p.min,p.max,p.count,units[csv.dataset.csv]].join(','));download(`s23-${csv.dataset.csv}-${s.range}.csv`,header+rows.join('\n'),'text/csv;charset=utf-8');}
    if(event.target.id==='load-more'){s.limit+=24;explorerRows();}
  });
  $('#content-region').addEventListener('input',event=>{if(event.target.id==='reading-search'){s.query=event.target.value;s.limit=24;explorerRows();}});
  $('#content-region').addEventListener('change',event=>{
    if(event.target.id==='reading-group'){s.group=event.target.value;s.limit=24;explorerRows();}
    if(event.target.id==='fit-samples'){s.fit=event.target.checked;save('fit',String(s.fit));for(const key of metrics[s.page]){const cached=cache.get(`${key}:${s.range}`);if(cached)drawHistory(key,cached.data);}document.querySelectorAll('.chart-period').forEach(p=>{p.textContent=`${s.range} · ${s.fit?'janela das amostras':'período completo'}`;});}
  });
  $('#refresh').addEventListener('click',()=>{cache.clear();refresh(true);});
  $('#pause').addEventListener('click',()=>{s.paused=!s.paused;$('#pause').textContent=s.paused?'Retomar':'Pausar';$('#pause').setAttribute('aria-pressed',String(s.paused));if(!s.paused)refresh();status();});
  $('#export').addEventListener('click',()=>{if(s.snapshot)download('s23-amostra.json',JSON.stringify(s.snapshot,null,2),'application/json');});
  $('#theme-button').addEventListener('click',()=>{document.body.classList.toggle('light');save('theme',document.body.classList.contains('light')?'light':'dark');});
  const picker=$('.project-switch');document.addEventListener('pointerdown',event=>{if(!picker.contains(event.target))picker.open=false;});picker.addEventListener('keydown',event=>{if(event.key==='Escape'){picker.open=false;picker.querySelector('summary').focus();}});
  document.addEventListener('visibilitychange',()=>{document.body.classList.toggle('motion-suspended',document.hidden);if(!document.hidden&&!s.paused)refresh();});
  window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)));
  setInterval(()=>{if(!document.hidden&&!s.paused)refresh();},15000);
  setInterval(()=>{$('#clock').textContent=new Date().toLocaleTimeString('pt-BR');status();},1000);
  navigate(location.hash.slice(1));refresh();
})();
