"""Source-backed scientific figures and a self-contained validation report."""
import base64,html,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiment import ROOT


def read(name):return json.loads((ROOT/'results'/name).read_text())


def table(headers,rows):
    return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def main():
    dev=read('development_v4.json');test=read('heldout_v4.json');traj=read('trajectory_v4.json')
    diag=read('rejection_diagnosis_v4.json');online=read('online_replay_v4.json');maps=read('radar_maps_v4.json')
    baseline=read('heldout_baseline_v3.json')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,2,figsize=(13,10),layout='constrained')
    colors={'truth':'#263f52','odometry':'#cf7c32','checked':'#21826b','robust_unverified':'#b34955'}
    for key,label in [('truth','Supplied reference'),('odometry','Radar odometry'),('checked','Checked-loop graph')]:
        points=np.array(traj['trajectories'][key]);axs[0,0].plot(points[:,0],points[:,1],label=label,color=colors[key],lw=2)
    axs[0,0].set(title='A. Real radar trajectory — 82 scans, 20.25 seconds',xlabel='Initial sensor-frame x (m)',ylabel='Initial sensor-frame y (m)');axs[0,0].axis('equal');axs[0,0].legend(fontsize=8);axs[0,0].grid(alpha=.2)
    labels=['v3 dev','v4 dev','v3 held-out','v4 held-out'];correct=[11,dev['summary']['correct_pose'],baseline['summary']['correct_pose'],test['summary']['correct_pose']];wrong=[0,dev['summary']['wrong_pose'],baseline['summary']['wrong_pose'],test['summary']['wrong_pose']]
    positions=np.arange(4);axs[0,1].bar(positions,correct,color='#21826b',label='Selected, pose-correct');axs[0,1].bar(positions,wrong,bottom=correct,color='#b34955',label='Selected, pose-wrong');axs[0,1].bar(positions,40-np.array(correct)-np.array(wrong),bottom=np.array(correct)+np.array(wrong),color='#dce3e6',label='Abstained')
    axs[0,1].set(xticks=positions,xticklabels=labels,ylim=(0,44),ylabel='Queries (40 per session)',title='B. Selection yield with explicit abstentions')
    for i,n in enumerate(correct):axs[0,1].text(i,n/2,str(n),ha='center',color='white',weight='bold')
    axs[0,1].legend(fontsize=8,loc='upper center')
    cells=np.array(maps['checked']['cells']);axs[1,0].scatter(cells[:,0],cells[:,1],s=1,c=np.log1p(cells[:,2]),cmap='Greys',alpha=.6,rasterized=True)
    path=np.array(traj['trajectories']['checked']);axs[1,0].plot(path[:,0],path[:,1],color='#21826b',lw=2)
    axs[1,0].set(title='C. Fused radar-return map (0.5 m cells)',xlabel='Initial sensor-frame x (m)',ylabel='Initial sensor-frame y (m)');axs[1,0].axis('equal');axs[1,0].grid(alpha=.15)
    names=['Radar\nodometry','Unchecked\nlinear graph','Unchecked\nrobust graph*','Checked\nlinear graph','Checked\nrobust graph']
    keys=['odometry','unverified_graph','robust_unverified_graph','checked_graph','robust_checked_graph'];values=[traj[k]['position_rmse_m'] for k in keys]
    axs[1,1].bar(np.arange(5),values,color=['#cf7c32','#b34955','#a97681','#21826b','#4ba68d'])
    axs[1,1].set(xticks=np.arange(5),xticklabels=names,ylabel='Position RMSE (m), log scale',title='D. Same segment, same initial-pose anchor');axs[1,1].set_yscale('log');axs[1,1].grid(axis='y',alpha=.2)
    for i,value in enumerate(values):axs[1,1].text(i,value*1.08,f'{value:.2f}',ha='center',fontsize=9)
    if not traj['robust_unverified_optimizer']['success']:
        axs[1,1].text(.02,.98,'* Robust unchecked: solver limit reached',transform=axs[1,1].transAxes,va='top',fontsize=8)
    fig.suptitle('Radar Loop Study · measured validation',fontsize=18,weight='bold')
    image=ROOT/'results/validation_figure.png';fig.savefig(image,dpi=160);plt.close(fig)
    encoded=base64.b64encode(image.read_bytes()).decode()
    resultrows=[]
    for name,data in [('v4 Development — September 02',dev),('v3 Held-out comparator — September 07',baseline),('v4 Held-out — September 07',test)]:
        s=data['summary'];resultrows.append([name,s['selected'],f"{s['correct_pose']}/{s['selected']}",s['abstained'],f"{s['median_translation_error_m']:.3f} m",f"{s['median_rotation_error_deg']:.3f}°"])
    graphrows=[]
    statuses={'unverified_graph':'unverified_optimizer','checked_graph':'checked_optimizer','robust_unverified_graph':'robust_unverified_optimizer','robust_checked_graph':'robust_checked_optimizer'}
    for name,key in zip(names,keys):
        s=traj[key];status='Not applicable' if key=='odometry' else ('Converged' if traj[statuses[key]]['success'] else 'Evaluation limit reached')
        graphrows.append([name.replace('\n',' '),f"{s['position_rmse_m']:.3f} m",f"{s['endpoint_position_error_m']:.3f} m",status])
    timingrows=[]
    for name,data in online['sessions'].items():timingrows.append([name,f"{data['median_image_to_decision_ms']:.1f} ms",f"{data['p95_image_to_decision_ms']:.1f} ms",f"{data['selected']}/40"])
    report='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Radar Validation Report</title><style>
    *{box-sizing:border-box}body{margin:0;color:#233743;background:#edf1ef;font:16px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:40px auto;background:white;padding:40px;border:1px solid #d7e0dc;border-radius:8px}h1{font-size:38px;line-height:1.1}h2{font-size:23px;margin-top:34px}small,.muted{color:#62747b}.tag{letter-spacing:.14em;text-transform:uppercase;font-size:12px;color:#21826b}.notice{padding:16px 20px;background:#fff5de;border-left:4px solid #c98d37}.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #dce5df;text-align:left}th{background:#f1f5f3}img{width:100%;height:auto}code{font-size:13px;overflow-wrap:anywhere}a{color:#21826b}li{margin:8px 0}@media(max-width:650px){main{margin:0;padding:20px;border:0}h1{font-size:30px}td,th{padding:7px}}@media print{body{background:white}main{border:0;margin:0;padding:10px}h2{break-after:avoid}table,img{break-inside:avoid}}
    </style></head><body><main><div class="tag">Ammara Noor · Independent research prototype · v4</div><h1>From radar matches to measured trajectory effects</h1><p class="muted">Relative-pose validation, development-only calibration, separate-session testing, short radar odometry, pose graphs and return-map fusion.</p>
    <div class="notice"><strong>Interpretation boundary.</strong> This is a small public-data study. The neural network is the authors’ frozen RadarLoc checkpoint. No new model training, lab-specific compatibility, target-device deployment or state-of-the-art claim is made. The trajectory is a short development segment, not an independent long-route SLAM benchmark.</div>'''
    report+='<h2>Measured overview</h2><img alt="Four scientific panels: trajectory, accepted-query counts, radar return map, and trajectory RMSE comparisons" src="data:image/png;base64,'+encoded+'">'
    report+='<h2>1 · Evaluate transforms, not just place proximity</h2><p>A selected pose meets the fixed evaluation criteria when translation error is at most 2 m and planar rotation error at most 5°. Errors use exact-time supplied sensor poses and the pinned pyboreas transform convention. Ground truth is excluded from inference.</p><div class="tablewrap">'+table(['Session','Selected','Pose-correct','Abstained','Median translation error','Median rotation error'],resultrows)+'</div>'
    report+='<p>Gate selection uses the already-inspected development session only. The frozen gate is overlap ≥0.70, inlier residual ≤1.5 m, angular support ≥6/12 sectors and estimated translation ≤40 m. No settings were tuned on held-out outcomes. The original v3 gate selects twelve correct held-out poses; v4 selects thirteen. This is a modest one-query improvement, not evidence of a broad breakthrough. Thirteen correct selections out of thirteen selected is not a reliability guarantee: twenty-seven held-out queries abstain.</p>'
    report+='<h2>2 · Diagnose failures with an explicitly separate oracle</h2><p>Among 41 development candidate pairs within 25 m, the new scan-only registration recovers '+str(diag['normal_correct_pairs'])+' poses within the error criteria. Ground-truth initialization recovers '+str(diag['oracle_correct_pairs'])+'. The remaining '+str(diag['initialization_limited_pairs'])+' initialization-limited pairs are an identified weakness. The oracle is diagnostic only and does not create exported decisions.</p><p>The old selected candidate 11.24 m away has approximately 0.14 m translation error. Failing a 10 m place label did not make its transform wrong.</p>'
    report+='<h2>3 · Actual motion and loop-factor effects</h2><p>82 consecutive radar scans span 20.25 seconds and about 122 m of travel. Consecutive ICP supplies odometry; no noisy-ground-truth trajectory is manufactured. Six temporally separated learned proposals supply estimated loop factors; three pass the frozen checks. All trajectories share the first pose anchor, with no fitted alignment.</p><div class="tablewrap">'+table(['Method','Position RMSE','Endpoint error','Optimizer status'],graphrows)+'</div>'
    report+='<p>Unchecked linear optimization is a negative control. The robust comparison uses a soft-L1 loss, with the same factor geometry and engineering scales. An optimizer reaching its evaluation limit is reported as such; it must not be presented as a converged baseline. The segment is too short to establish long-term drift performance, and graph residual scales are not calibrated covariance.</p>'
    report+='<h2>4 · Mapping and timing boundaries</h2><p>The map fuses radar returns with estimated checked-graph poses into 0.5 m cells. It is a return-support map, not a probabilistic occupancy grid. Dynamic clutter, free space and map accuracy are not evaluated. A PLY export accompanies the source results.</p><div class="tablewrap">'+table(['Replay session','Median image-to-decision','p95','Selected'],timingrows)+'</div><p>Timing includes query file I/O, preprocessing, neural inference, retrieval and candidate checks, with a warm reference database. It excludes sensor acquisition, transport and embedded hardware. These file-replay timings are not a live real-time guarantee.</p>'
    report+='<h2>5 · Reproduce and challenge the result</h2><p>Run <code>python run_upgrade.py</code> after installing <code>requirements-validation.txt</code>. Inspect <code>docs/UPGRADE_PROTOCOL.md</code>, <code>results/frozen_gate.json</code>, per-candidate JSON, loop diagnostics and source. The held-out session was substituted before inference because the initially chosen session lacked public pose labels.</p><p>Remaining work: other routes and weather conditions; motion distortion and dynamic-return handling; calibrated uncertainty; long-route temporal consistency; sensor adapters and target-device profiling. The lab’s internal architecture and current bottleneck remain unknown.</p><p class="muted">Boreas data: University of Toronto ASRL, CC BY 4.0. RadarLoc: Komorowski et al., upstream MIT licence. Original integration: MIT. Prepared with AI assistance; credit retained in the repository. Independent of IST.</p></main></body></html>'
    (ROOT/'Radar_Validation_Report.html').write_text(report)
    print('Created Radar_Validation_Report.html and results/validation_figure.png')

if __name__=='__main__':main()
