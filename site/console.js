'use strict';
const D=window.RADAR_STUDY;
const $=id=>document.getElementById(id);
const ns='http://www.w3.org/2000/svg';
const fmt=(v,n=2)=>Number.isFinite(v)?v.toFixed(n):'—';
const svgNode=(tag,attrs={},text)=>{const node=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,value));if(text!==undefined)node.textContent=text;return node;};
let currentView='trajectory',frame=D.trajectory.scans-1,playing=false,timer=null,selectedEvent=Math.max(0,D.trajectory.loops.length-1),queryId='query_423',candidateIndex=0;
const trajectories=D.trajectory.trajectories;
const queryGroups=new Map();
D.development.records.forEach(record=>{if(!queryGroups.has(record.query_id))queryGroups.set(record.query_id,[]);queryGroups.get(record.query_id).push(record);});
const queryFrames=Object.fromEntries(D.observations.queries.map(q=>[q.id,q]));
const referenceFrames=Object.fromEntries(D.observations.references.map(r=>[r.id,r]));
const gate=D.gate.gate;
function gateAssessment(v){
 const reasons=[];
 if((v.overlap??0)<gate.overlap)reasons.push('low overlap');
 if(v.rmse_m===null||v.rmse_m===undefined||v.rmse_m>gate.rmse_m)reasons.push('high residual');
 if((v.sector_coverage??0)<6)reasons.push('limited angular support');
 if(!v.translation_xy_m||Math.hypot(...v.translation_xy_m)>40)reasons.push('large translation');
 return {passed:reasons.length===0,reasons};
}
function showView(view){
 if(!['trajectory','observations','ledger'].includes(view))view='trajectory';
 currentView=view;stopPlayback();
 document.querySelectorAll('.view').forEach(panel=>panel.classList.toggle('active',panel.id==='view-'+view));
 document.querySelectorAll('[data-nav]').forEach(button=>{const active=button.dataset.nav===view;button.classList.toggle('active',active);if(button.getAttribute('role')==='tab')button.setAttribute('aria-selected',String(active));});
 if(view==='observations')renderObservations();
 if(view==='trajectory')renderTrajectory();
 try{history.replaceState(null,'','#'+view);}catch(_){}
}
document.querySelectorAll('[data-nav]').forEach(button=>button.addEventListener('click',event=>{event.preventDefault();showView(button.dataset.nav);}));
document.querySelector('.brand-mark').onclick=event=>{event.preventDefault();showView('trajectory');};
$('seeLedger').onclick=()=>showView('ledger');
function renderTrajectory(){
 const svg=$('trajectoryPlot');svg.replaceChildren();
 const W=1000,H=550,pad={left:80,right:80,top:70,bottom:85};
 const all=trajectories.truth.concat(trajectories.odometry,trajectories.checked);
 const bounds={x0:Math.min(...all.map(p=>p[0]))-7,x1:Math.max(...all.map(p=>p[0]))+9,y0:Math.min(...all.map(p=>p[1]))-9,y1:Math.max(...all.map(p=>p[1]))+12};
 const scale=Math.min((W-pad.left-pad.right)/(bounds.x1-bounds.x0),(H-pad.top-pad.bottom)/(bounds.y1-bounds.y0));
 const cx=(bounds.x0+bounds.x1)/2,cy=(bounds.y0+bounds.y1)/2;
 const px=x=>W/2+(x-cx)*scale,py=y=>(pad.top+H-pad.bottom)/2-(y-cy)*scale;
 const defs=svgNode('defs');const clip=svgNode('clipPath',{id:'plotClip'});clip.append(svgNode('rect',{x:40,y:48,width:920,height:410}));defs.append(clip);svg.append(defs);
 const field=svgNode('g',{'clip-path':'url(#plotClip)'});
 for(let x=-100;x<=150;x+=5){const major=x%10===0;field.append(svgNode('line',{x1:px(x),x2:px(x),y1:48,y2:458,stroke:major?'#344148':'#27343a','stroke-width':major?.65:.4}));if(major&&x>=-5&&x<=65)svg.append(svgNode('text',{x:px(x),y:477,fill:'#647b82','font-size':9,'font-family':'monospace','text-anchor':'middle'},x));}
 for(let y=-100;y<=100;y+=5){const major=y%10===0;field.append(svgNode('line',{x1:40,x2:960,y1:py(y),y2:py(y),stroke:major?'#344148':'#27343a','stroke-width':major?.65:.4}));if(major&&y>=-30&&y<=10)svg.append(svgNode('text',{x:28,y:py(y)+3,fill:'#647b82','font-size':9,'font-family':'monospace','text-anchor':'end'},y));}
 if($('showMap').checked){const cloud=svgNode('g',{'data-map':'returns'});D.maps.checked.cells.forEach(([x,y,count])=>{if(x<bounds.x0-5||x>bounds.x1+5||y<bounds.y0-5||y>bounds.y1+5)return;cloud.append(svgNode('circle',{cx:px(x),cy:py(y),r:Math.min(2.2,.8+Math.log1p(count)/3),fill:'#96a8a3',opacity:Math.min(.37,.07+count*.012)}));});field.append(cloud);}
 for(const [key,color,width,dash] of [['truth','#b8c6cb',1.8,'4 5'],['odometry','#e38a60',2,''],['checked','#a3d8c7',3.2,'']]){
  const points=trajectories[key].slice(0,frame+1);const path=points.map((p,i)=>(i?'L':'M')+px(p[0])+','+py(p[1])).join(' ');
  field.append(svgNode('path',{d:path,fill:'none',stroke:color,'stroke-width':width,'stroke-dasharray':dash,'stroke-linejoin':'round','stroke-linecap':'round','data-path':key}));
 }
 D.trajectory.loops.forEach((loop,i)=>{if(loop.query_index>frame)return;const q=trajectories.checked[loop.query_index],r=trajectories.checked[loop.reference_index];const passed=loop.verification.accepted;if(!passed)return;const x1=px(q[0]),y1=py(q[1]),x2=px(r[0]),y2=py(r[1]);const selected=i===selectedEvent;field.append(svgNode('path',{d:`M${x1},${y1} Q${(x1+x2)/2+24},${(y1+y2)/2-30} ${x2},${y2}`,fill:'none',stroke:'#d1966b','stroke-width':selected?1.7:1,opacity:selected?.9:.4,'stroke-dasharray':'3 4'}));field.append(svgNode('circle',{cx:x1,cy:y1,r:selected?7:4,fill:'#172128',stroke:'#d1966b','stroke-width':1.4}));});
 const current=trajectories.checked[frame];const x=px(current[0]),y=py(current[1]);
 field.append(svgNode('line',{x1:x-28,y1:y,x2:x+28,y2:y,stroke:'#a3d8c7','stroke-width':.7,opacity:.5}));field.append(svgNode('line',{x1:x,y1:y-28,x2:x,y2:y+28,stroke:'#a3d8c7','stroke-width':.7,opacity:.5}));field.append(svgNode('circle',{cx:x,cy:y,r:13,fill:'none',stroke:'#a3d8c7','stroke-width':.8,opacity:.6}));
 const heading=current[2];const direction=[Math.cos(heading),-Math.sin(heading)];const perp=[-direction[1],direction[0]];field.append(svgNode('polygon',{points:`${x+direction[0]*10},${y+direction[1]*10} ${x-direction[0]*6+perp[0]*5},${y-direction[1]*6+perp[1]*5} ${x-direction[0]*6-perp[0]*5},${y-direction[1]*6-perp[1]*5}`,fill:'#c7ece0'}));
 svg.append(field);
 svg.append(svgNode('text',{x:925,y:72,fill:'#7e969c','font-size':9,'font-family':'monospace','text-anchor':'end'},'Y+'));
 svg.append(svgNode('path',{d:'M942 90v-23m-4 5 4-5 4 5m-4 18h18',fill:'none',stroke:'#758a8e','stroke-width':1}));
 svg.append(svgNode('text',{x:960,y:106,fill:'#7e969c','font-size':9,'font-family':'monospace','text-anchor':'middle'},'X+'));
 $('plotFrame').textContent=String(frame+1).padStart(3,'0');$('plotTime').textContent='T + '+fmt(frame/(D.trajectory.scans-1)*D.trajectory.duration_s,2)+' s';$('frameCount').textContent=(frame+1)+' / '+D.trajectory.scans;$('frameSlider').max=D.trajectory.scans-1;$('frameSlider').value=frame;$('cursorPosition').textContent=fmt(current[0],1)+' / '+fmt(current[1],1)+' m';
}
function stopPlayback(){playing=false;if(timer)clearTimeout(timer);timer=null;$('playIcon').innerHTML='<path d="M6 3l11 7-11 7z"/>';$('play').setAttribute('aria-label','Play recorded trajectory');}
function tick(){if(!playing)return;if(frame>=D.trajectory.scans-1){stopPlayback();return;}frame++;renderTrajectory();timer=setTimeout(tick,(D.trajectory.duration_s*1000/(D.trajectory.scans-1))/Number($('speed').value));}
$('play').onclick=()=>{if(playing){stopPlayback();return;}if(frame>=D.trajectory.scans-1)frame=0;playing=true;$('playIcon').innerHTML='<path d="M5 3h3v14H5zm7 0h3v14h-3z"/>';$('play').setAttribute('aria-label','Pause recorded trajectory');renderTrajectory();timer=setTimeout(tick,(D.trajectory.duration_s*1000/(D.trajectory.scans-1))/Number($('speed').value));};
$('frameSlider').oninput=()=>{stopPlayback();frame=Number($('frameSlider').value);renderTrajectory();};$('showMap').onchange=renderTrajectory;
function renderEvents(){
 $('loopEvents').innerHTML=D.trajectory.loops.map((loop,i)=>`<button class="loop-event ${loop.verification.accepted?'passed':''} ${i===selectedEvent?'selected':''}" data-event="${i}"><i class="event-indicator"></i><span>${String(loop.reference_index+1).padStart(3,'0')} → ${String(loop.query_index+1).padStart(3,'0')}</span><span>${loop.verification.accepted?'GATE PASSED':'REJECTED'}</span></button>`).join('');
 document.querySelectorAll('[data-event]').forEach(button=>button.onclick=()=>{selectedEvent=Number(button.dataset.event);frame=D.trajectory.loops[selectedEvent].query_index;stopPlayback();renderEvents();renderTrajectory();});
 const loop=D.trajectory.loops[selectedEvent],v=loop.verification,e=loop.pose_error;
 $('eventInspection').innerHTML=`<div class="event-pair"><span>EVENT ${String(selectedEvent+1).padStart(2,'0')} / COSINE</span><b>${fmt(loop.cosine,4)}</b></div><div class="event-detail">Relative-pose error: <b>${fmt(e.translation_error_m,2)} m / ${fmt(e.rotation_error_deg,2)}°</b><br>${v.accepted?'Passed the fixed geometric gate.':v.reason.replaceAll('_',' ')}</div>`;
}
function renderObservations(){
 const filter=$('queryFilter').value,search=$('querySearch').value.toLowerCase().trim();
 const ids=[...queryGroups.keys()].filter(id=>{const selected=queryGroups.get(id).some(r=>gateAssessment(r.verification).passed);return id.toLowerCase().includes(search)&&(filter==='all'||(filter==='accepted'&&selected)||(filter==='abstain'&&!selected));});
 if(!ids.includes(queryId)){queryId=ids[0]??null;candidateIndex=0;}
 $('queryList').innerHTML=ids.length?ids.map(id=>{const selected=queryGroups.get(id).some(r=>gateAssessment(r.verification).passed);return `<button class="query-button ${id===queryId?'active':''} ${selected?'is-selected':''}" data-query="${id}"><span>${id.replace('query_','Q / ')}</span><i>${selected?'✓':'—'}</i></button>`;}).join(''):'<p class="empty-state">No observations match.</p>';
 document.querySelectorAll('[data-query]').forEach(button=>button.onclick=()=>{queryId=button.dataset.query;const index=queryGroups.get(queryId).findIndex(r=>gateAssessment(r.verification).passed);candidateIndex=index>=0?index:0;renderObservations();});
 $('observationMain').hidden=!queryId;$('pairInspector').hidden=!queryId;
 if(!queryId)return;
 const candidates=queryGroups.get(queryId),record=candidates[candidateIndex],v=record.verification,error=record.pose_error,assessment=gateAssessment(v);
 $('scanTitle').textContent=queryId.replace('query_','Observation / ');$('scanBadge').textContent=assessment.passed?'PROVISIONAL / GATE PASSED':'REJECTED BY GEOMETRY';$('scanBadge').className='status-badge'+(assessment.passed?' pass':'');
 $('queryImage').src=D.observations.images[queryId];$('referenceImage').src=D.observations.images[record.reference_id];
 $('queryImageCaption').textContent=queryId+' · 02 SEP 2021';$('referenceImageCaption').textContent=record.reference_id+' · 05 AUG 2021';
 $('pairAssessment').innerHTML=`<div class="pair-verdict ${assessment.passed?'pass':''}">${assessment.passed?'Passed verification checks.':'Candidate rejected.'}</div><div class="pair-reason">${assessment.passed?'PASSES FROZEN DEVELOPMENT GATE':assessment.reasons.join(' / ').toUpperCase()}</div><div class="pair-stats"><div><span>Learned cosine</span><b>${fmt(record.score,4)}</b></div><div><span>Supplied-position separation</span><b>${fmt(record.distance_m,1)} m</b></div><div><span>Return overlap</span><b>${fmt(v.overlap*100,1)}% / ≥${fmt(gate.overlap*100,0)}%</b></div><div><span>Inlier residual</span><b>${fmt(v.rmse_m,2)} m / ≤${fmt(gate.rmse_m,1)} m</b></div><div><span>Angular support</span><b>${v.sector_coverage??0} / 12</b></div><div class="evaluation"><span>Translation error</span><b>${fmt(error.translation_error_m,2)} m</b></div><div class="evaluation"><span>Rotation error</span><b>${fmt(error.rotation_error_deg,2)}°</b></div></div>`;
 $('candidateList').innerHTML=candidates.map((r,i)=>`<button class="candidate-button ${i===candidateIndex?'active':''}" data-candidate="${i}"><b>0${i+1}</b><span>${r.reference_id.replace('reference_','REF / ')}</span><span>${fmt(r.score,3)}</span></button>`).join('');
 document.querySelectorAll('[data-candidate]').forEach(button=>button.onclick=()=>{candidateIndex=Number(button.dataset.candidate);renderObservations();});
 renderAlignment(record);
}
function renderAlignment(record){
 const svg=$('alignmentPlot');svg.replaceChildren();const v=record.verification;
 if(v.yaw_rad===undefined){svg.append(svgNode('text',{x:20,y:40,fill:'#98afa8','font-size':12},'Insufficient returns for alignment'));return;}
 const c=Math.cos(v.yaw_rad),s=Math.sin(v.yaw_rad),t=v.translation_xy_m;
 const source=D.observations.points[record.query_id].map(([x,y])=>[c*x-s*y+t[0],s*x+c*y+t[1]]),target=D.observations.points[record.reference_id];
 const all=source.concat(target),extent=Math.max(...all.map(p=>Math.max(Math.abs(p[0]),Math.abs(p[1]))),1)*1.05,scale=125/extent;
 for(let n=-2;n<=2;n++){svg.append(svgNode('line',{x1:400+n*125,y1:25,x2:400+n*125,y2:285,stroke:'#344449','stroke-width':.5}));svg.append(svgNode('line',{x1:90,y1:155+n*62.5,x2:710,y2:155+n*62.5,stroke:'#344449','stroke-width':.5}));}
 for(const [points,color] of [[target,'#87b9a8'],[source,'#d6905b']]){const group=svgNode('g',{fill:color,opacity:.68});points.forEach(([x,y])=>group.append(svgNode('circle',{cx:400+x*scale,cy:155-y*scale,r:1.6})));svg.append(group);}
 svg.append(svgNode('text',{x:16,y:21,fill:'#7f9996','font-family':'monospace','font-size':9},'EQUAL AXIS SCALE / EXTENT ±'+fmt(extent,0)+' M'));
 svg.append(svgNode('text',{x:16,y:293,fill:'#7f9996','font-family':'monospace','font-size':9},'ESTIMATED TRANSFORM / NO SUPPLIED-POSE INITIALIZATION'));
}
$('queryFilter').onchange=()=>{candidateIndex=0;renderObservations();};$('querySearch').oninput=()=>{candidateIndex=0;renderObservations();};
function renderLedger(){
 const dev=D.development.summary,held=D.heldout.summary,baseline=D.heldoutBaseline.summary;
 $('yieldBars').innerHTML=[['V3 / development',11],['V4 / development',dev.correct_pose],['V3 / held-out',baseline.correct_pose],['V4 / held-out',held.correct_pose]].map(([label,count])=>`<div class="yield-row"><span>${label}</span><div class="yield-bar"><i style="width:${count/40*100}%"></i></div><strong>${count}/40</strong></div>`).join('');
 $('heldoutFacts').innerHTML=[['Abstained',`${held.abstained} / 40`],['Median translation error',fmt(held.median_translation_error_m,3)+' m'],['Median rotation error',fmt(held.median_rotation_error_deg,3)+'°']].map(([a,b])=>`<div><dt>${a}</dt><dd>${b}</dd></div>`).join('');
 const T=D.trajectory;
 $('graphTable').innerHTML=[['Radar odometry','odometry',null],['Unchecked / linear graph','unverified_graph','unverified_optimizer'],['Unchecked / robust graph','robust_unverified_graph','robust_unverified_optimizer'],['Checked / linear graph','checked_graph','checked_optimizer'],['Checked / robust graph','robust_checked_graph','robust_checked_optimizer']].map(([label,key,status])=>{const ok=status?T[status].success:null;return `<tr class="${key==='checked_graph'?'highlight':''}"><td>${label}</td><td>${fmt(T[key].position_rmse_m,3)} m</td><td>${fmt(T[key].endpoint_position_error_m,3)} m</td><td class="solver-status ${ok===false?'limit':''}">${ok===null?'NOT APPLICABLE':ok?'CONVERGED':'SOLVER LIMIT'}</td></tr>`;}).join('');
 const timing=D.replay.sessions.heldout;
 $('timingFacts').innerHTML=`<div class="timing-row"><span>Held-out image-to-decision / median</span><b>${fmt(timing.median_image_to_decision_ms,1)} ms</b></div><div class="timing-row"><span>Held-out image-to-decision / p95</span><b>${fmt(timing.p95_image_to_decision_ms,1)} ms</b></div><p class="timing-description">CPU file replay, warm reference database. Includes query I/O, preprocessing, inference and checks. Excludes live acquisition and target-device transport.</p>`;
 $('checkpointHash').textContent=D.development.model.checkpoint_sha256;
}
$('methodsOpen').onclick=()=>{$('methodsDialog').showModal();};$('methodsClose').onclick=()=>{$('methodsDialog').close();};$('methodsDialog').onclick=event=>{if(event.target===$('methodsDialog')){const rect=$('methodsDialog').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)$('methodsDialog').close();}};
$('exportRecord').onclick=()=>{
 let record;
 if(currentView==='trajectory')record={view:currentView,frame:frame+1,estimated_pose:trajectories.checked[frame],loop:D.trajectory.loops[selectedEvent],trajectory_scope:D.trajectory.scope};
 else if(currentView==='observations')record={view:currentView,query_id:queryId,candidates:queryId?queryGroups.get(queryId):[]};
 else record={view:currentView,development:D.development.summary,heldout:D.heldout.summary,baseline:D.heldoutBaseline.summary,frozen_gate:D.gate.gate};
 const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));link.download='radar-'+currentView+'-record.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
 $('toast').textContent='Experiment record exported.';$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2200);
};
$('trajectoryRmse').textContent=fmt(D.trajectory.checked_graph.position_rmse_m,3);
$('odometryRmse').textContent=fmt(D.trajectory.odometry.position_rmse_m,3)+' m';
$('checkedRmse').textContent=fmt(D.trajectory.checked_graph.position_rmse_m,3)+' m';
$('endpointError').textContent=fmt(D.trajectory.checked_graph.endpoint_position_error_m,3)+' m';
$('rmseReduction').textContent='↘ '+fmt((1-D.trajectory.checked_graph.position_rmse_m/D.trajectory.odometry.position_rmse_m)*100,1)+'%';
$('scanTotal').textContent=D.trajectory.scans;
$('distanceTotal').textContent=fmt(D.trajectory.ground_truth_path_length_m,1);
$('loopTotal').innerHTML=String(D.trajectory.checked_loops).padStart(2,'0')+' <small>/ '+String(D.trajectory.loop_proposals).padStart(2,'0')+' checked</small>';
renderEvents();renderTrajectory();renderLedger();showView(location.hash.slice(1)||'trajectory');
window.addEventListener('pagehide',stopPlayback);
