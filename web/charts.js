/* Original SVG history renderer. Averages and extrema stay separate. */
(() => {
  'use strict';
  const charts = new WeakMap();
  const fmt = (v, d=1) => Number.isFinite(v) ? v.toLocaleString('pt-BR', {maximumFractionDigits:d}) : '—';
  const time = t => new Date(t).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const safe = v => String(v).replace(/[&<>"']/g, x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  function tooltipPosition(x, y, width, height, tipWidth, tipHeight) {
    const left=Math.max(8,Math.min(width-tipWidth-8,x+16));
    const top=y-tipHeight-14>=8?y-tipHeight-14:y+18;
    return {x:left,y:Math.max(8,Math.min(height-tipHeight-8,top))};
  }
  function dispose(host) {
    const old=charts.get(host);
    if(old?.frame)cancelAnimationFrame(old.frame);
    charts.delete(host);
  }
  function geometry(points, {start,end,fit=false,percent=false,interval=30,width=700}={}) {
    const data=points.filter(p=>Number.isFinite(p.time)&&Number.isFinite(p.value));
    if (!data.length) return null;
    let a=start, b=end;
    if (fit) {
      a=data[0].firstTime ?? data[0].time;
      b=data.at(-1).time;
      const pad=Math.max(interval*1000,(b-a)*.04);
      a-=pad; b+=pad;
    }
    if (!(b>a)) b=a+60000;
    let low=Math.min(...data.map(p=>p.min??p.value)), high=Math.max(...data.map(p=>p.max??p.value));
    if (percent) {low=0;high=100;}
    else {
      const pad=Math.max((high-low)*.15,Math.abs(high)*.02,.01);
      low-=pad; high+=pad;
      if(data.every(p=>p.value>=0)) low=Math.max(0,low);
    }
    const x=t=>54+(t-a)/(b-a)*(width-72), y=v=>16+(high-v)/(high-low)*160;
    const groups=[]; let group=[];
    for (const p of data) {
      const previous=group.at(-1);
      if(previous && ((p.firstTime??p.time)-(previous.lastTime??previous.time)>interval*3000 || p.maxGapSec>interval*3)) {
        groups.push(group);group=[];
      }
      group.push(p);
    }
    if(group.length) groups.push(group);
    return {data,groups,a,b,low,high,x,y};
  }
  function draw(host, payload, options) {
    dispose(host);
    const width=host.clientWidth<430?400:700;
    const g=geometry(payload.points,{...options,width});
    if(!g) {host.innerHTML='<div class="chart-empty">Nenhuma amostra neste período.</div>';return;}
    const {data,groups,x,y,a,b,low,high}=g;
    const grid=[0,.5,1].map(f=>`<line class="gridline" x1="54" x2="${width-18}" y1="${16+f*160}" y2="${16+f*160}"/><text class="axis" x="46" y="${20+f*160}" text-anchor="end">${fmt(high-f*(high-low))}</text>`).join('');
    const paths=groups.map(group=>{
      const line=group.map((p,i)=>`${i?'L':'M'}${x(p.time).toFixed(2)} ${y(p.value).toFixed(2)}`).join(' ');
      const upper=group.map(p=>`${x(p.time).toFixed(2)},${y(p.max??p.value).toFixed(2)}`);
      const lower=[...group].reverse().map(p=>`${x(p.time).toFixed(2)},${y(p.min??p.value).toFixed(2)}`);
      return `<polygon class="envelope" points="${[...upper,...lower].join(' ')}"/><path class="line" d="${line}"/>`+
        group.map(p=>`<circle class="sample-dot" cx="${x(p.time)}" cy="${y(p.value)}" r="${data.length<50?2.5:1.3}"/>`).join('');
    }).join('');
    const label=t=>new Date(t).toLocaleString('pt-BR',b-a>86400000?{day:'2-digit',month:'2-digit'}:{hour:'2-digit',minute:'2-digit'});
    host.innerHTML=`<svg viewBox="0 0 ${width} 208" tabindex="0" role="img" aria-label="${safe(options.label)}. ${data.length} pontos. Use as setas para explorar; Home e End para os extremos.">${grid}${paths}<line class="crosshair" x1="54" x2="54" y1="16" y2="176" hidden/><circle class="selected-dot" cx="54" cy="16" r="4" hidden/><text class="axis" x="54" y="201">${safe(label(a))}</text><text class="axis" x="${width-18}" y="201" text-anchor="end">${safe(label(b))}</text></svg><div class="chart-tooltip" role="tooltip" aria-hidden="true"></div><div class="chart-readout" aria-live="polite">Passe o cursor, toque ou use as setas para inspecionar uma amostra.</div>`;
    const record={...g,options,index:0,frame:0,visible:false};charts.set(host,record);
    const svg=host.querySelector('svg');
    const select=event=>{
      const box=event.currentTarget.getBoundingClientRect();
      const target=(event.clientX-box.left)/box.width*width;
      let index=0;
      data.forEach((p,i)=>{if(Math.abs(x(p.time)-target)<Math.abs(x(data[index].time)-target))index=i;});
      inspect(host,index);
    };
    svg.addEventListener('pointermove',select);
    svg.addEventListener('pointerdown',select);
    svg.addEventListener('click',()=>{svg.focus({preventScroll:true});inspect(host,record.index);});
    svg.addEventListener('pointerleave',()=>{if(document.activeElement!==svg)hide(host);});
    svg.addEventListener('blur',()=>hide(host));
    svg.addEventListener('focus',()=>inspect(host,record.index));
    svg.addEventListener('keydown',event=>{
      if(event.key==='Escape'){hide(host);return;}
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
      event.preventDefault();
      const i=event.key==='Home'?0:event.key==='End'?data.length-1:record.index+(event.key==='ArrowRight'?1:-1);
      inspect(host,Math.max(0,Math.min(data.length-1,i)));
    });
  }
  function inspect(host,index) {
    const r=charts.get(host),p=r.data[index];r.index=index;
    const line=host.querySelector('.crosshair'),dot=host.querySelector('.selected-dot');
    line.removeAttribute('hidden');dot.removeAttribute('hidden');
    const tip=host.querySelector('.chart-tooltip');
    const changed=r.lastIndex!==index;
    if(changed) {
      tip.innerHTML=`<div class="tooltip-date">${safe(time(p.time))}</div><div class="tooltip-value"><span><i></i>${safe(r.options.label)}</span><strong>${safe(fmt(p.value,4))} ${safe(r.options.unit)}</strong></div><div class="tooltip-extrema"><span>Mín <b>${safe(fmt(p.min??p.value,4))}</b></span><span>Máx <b>${safe(fmt(p.max??p.value,4))}</b></span></div><div class="tooltip-count">${p.count??1} amostra(s) · ${p.count>1?'resumo agregado':'leitura registrada'}</div>`;
      host.querySelector('.chart-readout').textContent=`${time(p.time)} · Média ${fmt(p.value,4)} ${r.options.unit} · Mín ${fmt(p.min??p.value,4)} · Máx ${fmt(p.max??p.value,4)} · ${p.count??1} amostra(s)`;
      r.lastIndex=index;
    }
    const svg=host.querySelector('svg'),box=svg.getBoundingClientRect();
    const vb=svg.viewBox.baseVal;
    const scale=Math.min(box.width/vb.width,box.height/vb.height);
    const offsetX=(box.width-vb.width*scale)/2,offsetY=(box.height-vb.height*scale)/2;
    const target=tooltipPosition(offsetX+r.x(p.time)*scale,offsetY+r.y(p.value)*scale,host.clientWidth,host.clientHeight,tip.offsetWidth,tip.offsetHeight);
    r.target={...target,cx:r.x(p.time),cy:r.y(p.value)};
    if(!r.visible||reduced())r.position={...r.target};
    r.visible=true;tip.classList.add('is-visible');tip.setAttribute('aria-hidden','false');
    if(!r.frame)animate(host);
  }
  function animate(host) {
    const r=charts.get(host);if(!r||!r.visible)return;
    const factor=reduced()?1:.24;
    let distance=0;
    for(const key of ['x','y','cx','cy']){const delta=r.target[key]-r.position[key];distance=Math.max(distance,Math.abs(delta));r.position[key]+=Math.abs(delta)<.25?delta:delta*factor;}
    const p=r.position,line=host.querySelector('.crosshair'),dot=host.querySelector('.selected-dot');
    host.querySelector('.chart-tooltip').style.transform=`translate3d(${p.x}px,${p.y}px,0)`;
    line.setAttribute('x1',p.cx);line.setAttribute('x2',p.cx);dot.setAttribute('cx',p.cx);dot.setAttribute('cy',p.cy);
    r.frame=distance>.25?requestAnimationFrame(()=>animate(host)):0;
  }
  function hide(host) {
    const r=charts.get(host);if(!r)return;r.visible=false;
    if(r.frame)cancelAnimationFrame(r.frame);r.frame=0;
    const tip=host.querySelector('.chart-tooltip');tip.classList.remove('is-visible');tip.setAttribute('aria-hidden','true');
    host.querySelector('.crosshair').setAttribute('hidden','');host.querySelector('.selected-dot').setAttribute('hidden','');
  }
  function destroy(root){root.querySelectorAll('.chart').forEach(dispose);}
  window.S23Charts={draw,geometry,tooltipPosition,destroy};
})();
