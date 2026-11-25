import sys,json,pickle,time; sys.path.insert(0,'.')
from evalx import *
from scipy.optimize import brentq
OUT='results/'   # output folder

def ema_sigma(q,tau_e,nname):
    t,x,tr,lvl=get(nname)
    class Probe:
        def __init__(s): s.e=0;s.v=[]
        def step(s): return 1.0
        def update(s,nu,S): s.e+=DT/tau_e*(nu-s.e); s.v.append(s.e)
    pr=Probe(); kalman(x,q,R_KF,qfun=pr); return np.array(pr.v)[t>10].std()

# ---------- grid of adaptive configs, evaluated on every run once ----------
# sig0 (innovation scale) is a noise-only number; it is taken from the TRAINING noise run of each fold.
N=['run_N_1.csv','run_N_2.csv']; S=['run_1_r1.csv','run_1_r2.csv','run_1_r3.csv']
grid=[]
for q in [1e-4,3e-4,1e-3]:
  for tau_e in [0.3,0.6,1.0]:
    for z0 in [0.5,1.0,1.5,2.5]:
      for dz in [1.0,2.0]:
        for ratio in [100,1000,5000]:
          for tdec in [1.0,3.0]:
            grid.append((q,tau_e,z0,dz,ratio,tdec))
grid=grid[::2]          # every second config (keeps tau_dec = 1 s) -> 216 configs
import os
from multiprocessing import Pool
def eval_cfg(args):
    (q,tau_e,z0,dz,ratio,tdec),src=args
    p=dict(q=q,tau_e=tau_e,z0=z0,z1=z0+dz,ratio=ratio,tau_dec=tdec,sig0=ema_sigma(q,tau_e,src))
    c=dict(p=p)
    for n in N: c['s_'+n]=noise_sigma('akf',names=(n,),**p)
    for n in S: c['r_'+n]=step_response('akf',(n,),**p)[0]
    return c
CACHE=OUT+'cv_cache_clean.pkl'
t0=time.time()
if os.path.exists(CACHE): caches=pickle.load(open(CACHE,'rb'))
else:
    caches={}
    with Pool(4) as pool:
        for src in N: caches[src]=pool.map(eval_cfg,[(g,src) for g in grid])
    pickle.dump(caches,open(CACHE,'wb'))
print('grid done %.0f s'%(time.time()-t0),flush=True)

def t90_of(resps): return t90(np.mean(resps,0))[0]
def os_of(resps): return overshoot(np.mean(resps,0))
folds=[dict(name='A',trN='run_N_1.csv',teN='run_N_2.csv',trS=['run_1_r1.csv'],teS=['run_1_r2.csv','run_1_r3.csv'],teR=(2,3)),
       dict(name='B',trN='run_N_2.csv',teN='run_N_1.csv',trS=['run_1_r2.csv'],teS=['run_1_r1.csv','run_1_r3.csv'],teR=(1,3))]
out={}
for f in folds:
    # select: among configs whose TRAIN noise <= 1.5, minimise TRAIN t90
    cand=[(t90_of([c['r_'+n] for n in f['trS']]),c) for c in caches[f['trN']] if c['s_'+f['trN']]<=1.5]
    t9,csel=min(cand,key=lambda a:a[0]); P=csel['p']; s_tr=csel['s_'+f['trN']]
    # matched baselines on TRAIN noise
    fc=brentq(lambda v:noise_sigma('lp',names=(f['trN'],),fc=v)-s_tr,0.002,1.5)
    qm=np.exp(brentq(lambda v:noise_sigma('kf',names=(f['trN'],),q=np.exp(v))-s_tr,np.log(1e-6),np.log(1e-1)))
    qr=np.exp(brentq(lambda v:noise_sigma('rts',names=(f['trN'],),q=np.exp(v))-s_tr,np.log(1e-9),np.log(1e2)))
    fz=brentq(lambda v:noise_sigma('zp',names=(f['trN'],),fc=v)-s_tr,0.002,1.5)
    meths={'zero-phase LP (non-causal)':('zp',dict(fc=fz)),'Kalman+RTS (non-causal)':('rts',dict(q=qr)),
           'causal LP':('lp',dict(fc=fc)),'fixed-Q Kalman':('kf',dict(q=qm)),'adaptive-Q Kalman':('akf',P)}
    fo={'selected':P,'train_sigma':s_tr,'train_t90':t9,'fc':fc,'q_kf':qm,'q_rts':qr,'fc_zp':fz,'methods':{}}
    for name,(k,p) in meths.items():
        r={}
        r['sigma_test']=noise_sigma(k,names=(f['teN'],),**p)
        m,_=step_response(k,tuple(f['teS']),**p); r['t90']=t90(m)[0]; r['os']=overshoot(m)
        for mode in [1,2,3,4,5]:
            r['rmse%d'%mode]=rmse(k,tuple('run_%d_r%d.csv'%(mode,i) for i in f['teR']),**p)
        fo['methods'][name]=r
    out[f['name']]=fo
    print('fold',f['name'],'sel',P,'train sigma %.2f t90 %.2f'%(s_tr,t9),flush=True)
    for name,r in fo['methods'].items(): print('  %-28s'%name,{a:round(float(b),2) for a,b in r.items()},flush=True)
json.dump(out,open(OUT+'cv_results.json','w'),indent=1,default=float)
print('ALL DONE',time.time()-t0,flush=True)
