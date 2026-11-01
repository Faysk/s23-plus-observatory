const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../web/charts.js'),'utf8'),context);
const geometry=context.window.S23Charts.geometry;
assert.equal(geometry([],{}),null);
const points=[{time:100000,value:20,min:0,max:80,count:2},{time:130000,value:25,min:25,max:25},{time:600000,value:40,min:40,max:40}];
const g=geometry(points,{start:0,end:3600000,fit:true,percent:true,interval:30});
assert.equal(g.low,0);assert.equal(g.high,100);assert.equal(g.groups.length,2);
assert.ok(g.b-g.a<3600000,'fit should display the actual sampled window');
const spike=geometry([{time:100000,value:50,min:1,max:99}],{start:0,end:200000});
assert.ok(spike.low<1&&spike.high>99,'axis must retain the recorded extrema');
console.log('Chart geometry: empty state, gaps, percent limits, sample fit and spike preservation passed.');
const position=context.window.S23Charts.tooltipPosition;
for(const [x,y]of [[0,0],[400,200],[190,80]]){
 const p=position(x,y,320,250,252,135);
 assert.ok(p.x>=8&&p.x+252<=312,'tooltip must stay within mobile horizontal bounds');
 assert.ok(p.y>=8&&p.y+135<=242,'tooltip must stay within vertical bounds');
}
console.log('Tooltip edge placement: passed.');
