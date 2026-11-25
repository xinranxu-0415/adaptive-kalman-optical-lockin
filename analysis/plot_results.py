from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from evalx import get,run_est,step_response
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'figures'; out.mkdir(exist_ok=True)
r=json.loads((ROOT/'results/results.json').read_text())
methods={'Causal LP':('lp',dict(fc=r['fc_matched'])),'Fixed-Q KF':('kf',dict(q=r['q_matched'])),'Adaptive-Q KF':('akf',r['AQ'])}
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
for label,(k,p) in methods.items():
    m,_=step_response(k,('run_1_r2.csv','run_1_r3.csv'),**p)
    ax.plot(np.arange(len(m))/200.-3,m,label=label)
ax.axhline(.9,color='.5',ls=':',label='90% level'); ax.set(xlabel='Time after commanded step (s)',ylabel='Normalized response',xlim=(-1,9)); ax.legend()
fig.savefig(out/'single_split_step_response.pdf'); fig.savefig(out/'single_split_step_response.png',dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
t,x,tr,lvl=get('run_4_r2.csv'); ax.plot(t,tr,'k--',label='Calibration-derived reference')
for label,(k,p) in methods.items(): ax.plot(t,run_est(k,x,**p)[0],label=label,lw=1.3)
ax.set(xlabel='Time (s)',ylabel='Demodulated amplitude (ADC counts)',xlim=(5,60)); ax.legend(fontsize=9)
fig.savefig(out/'sine_tracking.pdf'); fig.savefig(out/'sine_tracking.png',dpi=180); plt.close(fig)
print('Saved regenerated step-response and sine-tracking figures.')
