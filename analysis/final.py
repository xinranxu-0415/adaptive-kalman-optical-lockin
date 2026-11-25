import sys,json,pickle; sys.path.insert(0,'.')
from evalx import *
from scipy.optimize import brentq
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
OUT=str(Path(__file__).resolve().parents[1] / 'results')+'/'
Path(OUT).mkdir(exist_ok=True)
TRN_N=('run_N_1.csv',); TST_N=('run_N_2.csv',)
TRN_S=('run_1_r1.csv',); TST_S=('run_1_r2.csv','run_1_r3.csv')
TST_S2=('run_2_r2.csv','run_2_r3.csv')
# ---- adaptive config chosen on TRAIN (N_1, run_1_r1) ----
def ema_sigma(q,tau_e):
    t,x,tr,lvl=get('run_N_1.csv')
    from pipe import _fast_kf
    ev=_fast_kf(x,q,R_KF,float(x[:200].mean()),False,1.,DT/tau_e,1.,4.,300.,DT)[2]
    return ev[t>10].std()
AQ=dict(q=3e-4,tau_e=1.0,z0=2.5,z1=3.5,ratio=5000.,tau_dec=3.0); AQ['sig0']=ema_sigma(AQ['q'],AQ['tau_e'])
s_ad=noise_sigma('akf',names=TRN_N,**AQ)
# ---- matched-noise baselines on TRAIN ----
fc_m=brentq(lambda f:noise_sigma('lp',names=TRN_N,fc=f)-s_ad,0.03,0.3)
q_m=np.exp(brentq(lambda lq:noise_sigma('kf',names=TRN_N,q=np.exp(lq))-s_ad,np.log(1e-5),np.log(1e-2)))
print('train sigma adaptive %.3f -> LP fc=%.3f Hz, KF q=%.2e'%(s_ad,fc_m,q_m))
methods={
 'Lab 3: zero-phase LP (non-causal)':('zp',dict(fc=0.1)),
 'Causal LP (matched noise)':('lp',dict(fc=fc_m)),
 'Fixed-Q Kalman (matched noise)':('kf',dict(q=q_m)),
 'Adaptive-Q Kalman':('akf',AQ),
}
res={}
for name,(k,p) in methods.items():
    r={}
    r['sigma_train_N1']=noise_sigma(k,names=TRN_N,**p)
    r['sigma_test_N2']=noise_sigma(k,names=TST_N,**p)
    m,_=step_response(k,TST_S,**p); r['t90_large_s']=t90(m)[0]; r['rise10_90_s']=t90(m)[1]; r['overshoot_large']=overshoot(m)
    try:
        m2,_=step_response(k,TST_S2,**p); r['t90_small_s']=t90(m2)[0]; r['overshoot_small']=overshoot(m2)
    except Exception as e: r['t90_small_s']=None
    for mode in [1,2,3,4,5]:
        r['rmse_run%d'%mode]=rmse(k,tuple('run_%d_r%d.csv'%(mode,i) for i in (2,3)),**p)
    res[name]=r
    print(name); print({a:(round(b,3) if b is not None else None) for a,b in r.items()})
json.dump(dict(AQ=AQ,fc_matched=fc_m,q_matched=q_m,results=res),open(OUT+'results.json','w'),indent=1)
