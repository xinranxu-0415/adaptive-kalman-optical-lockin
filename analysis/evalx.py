import numpy as np, sys
sys.path.insert(0,'.')
from pipe import *
LS,AS=calib_map('run_K_pre.csv')
PCOEF=np.polyfit(LS,AS,2)
def truth(lvl): return np.polyval(PCOEF,lvl)
_cache={}
def get(name):
    if name not in _cache:
        t,y,ref,lvl,noi=load(name); x=demod(y,ref,LAG)
        _cache[name]=(t,x,truth(lvl),lvl)
    return _cache[name]

R_KF=14.0**2   # raw demod variance (measured on N_1, N_2: std ~14-15.7)

def run_est(kind,x,**p):
    if kind=='zp': return lp_zerophase(x,p.get('fc',0.1)),None
    if kind=='lp': return lp_causal(x,p['fc']),None
    if kind=='kf': return kalman(x,p['q'],R_KF)
    if kind=='rts': return rts(x,p['q'],R_KF),None
    if kind=='akf':
        ad=AdaptQ(p['sig0'],p.get('tau_e',0.4),p.get('z0',1.0),p.get('z1',4.0),p.get('ratio',300.),p.get('tau_dec',1.0))
        return kalman(x,p['q'],R_KF,qfun=ad)
    raise ValueError

def noise_sigma(kind,names=('run_N_1.csv',),tskip=10.0,**p):
    out=[]
    for n in names:
        t,x,tr,lvl=get(n); a,_=run_est(kind,x,**p); m=t>tskip
        out.append(a[m].std())
    return float(np.mean(out))

def step_events(lvl,t,min_jump=40):
    idx=np.where(np.abs(np.diff(lvl))>=min_jump)[0]+1
    return idx

def step_response(kind,names,pre=3.0,post=9.0,**p):
    """ensemble-average normalised step response (up and down steps, sign-normalised)."""
    n_pre=int(pre*FS); n_post=int(post*FS); resp=[]
    for n in names:
        t,x,tr,lvl=get(n); a,_=run_est(kind,x,**p)
        for i in step_events(lvl,t):
            if i-n_pre<0 or i+n_post>len(a): continue
            before=a[i-int(1.0*FS):i].mean(); target=tr[i+int(3*FS)]  # truth after step (constant within segment)
            tb=tr[i-int(1.0*FS)]; step=target-tb
            if abs(step)<3: continue
            r=(a[i-n_pre:i+n_post]-tb)/step
            resp.append(r)
    resp=np.array(resp); return resp.mean(0),resp

def t90(r,pre=3.0):
    k0=int(pre*FS); lo=0.1;hi=0.9
    r=r[k0:]
    ihi=np.argmax(r>=hi) if (r>=hi).any() else len(r)
    ilo=np.argmax(r>=lo) if (r>=lo).any() else 0
    return (ihi)/FS, (ihi-ilo)/FS
def overshoot(r,pre=3.0):
    k0=int(pre*FS); return max(r[k0:].max()-1.0,0.0)

def rmse(kind,names,tskip=5.0,**p):
    out=[]
    for n in names:
        t,x,tr,lvl=get(n); a,_=run_est(kind,x,**p); m=t>tskip
        out.append(np.sqrt(np.mean((a[m]-tr[m])**2)))
    return float(np.mean(out))
