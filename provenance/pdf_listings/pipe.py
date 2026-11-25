import numpy as np
from scipy import signal
from load import load
FS=200.0; DT=1/FS

def sos_lp(fc,order=2): return signal.butter(order,fc,fs=FS,output='sos')

def hp_causal(y,fc=0.7):
    b=signal.sosfilt(sos_lp(fc),y-y[:200].mean())  # remove offset to limit start transient
    return (y-y[:200].mean())-b

def delay(ref,lag_s):
    n=int(round(lag_s*FS))
    out=np.empty_like(ref); out[:n]=ref[0]; out[n:]=ref[:-n] if n>0 else ref
    return out

def est_lag(y,ref,lags=np.arange(0,0.25,0.005)):
    h=hp_causal(y)
    sc=[]
    for L in lags:
        sc.append(np.mean(h[400:]*delay(ref,L)[400:]))
    sc=np.array(sc); return lags[np.argmax(sc)],lags,sc

def demod(y,ref,lag):
    return hp_causal(y)*delay(ref,lag)

LAG=0.015
def calib_map(name='run_K_pre.csv',tskip=3.0):
    """steady-state mean of demod output (after 0.1 Hz LP is replaced by plain mean) per commanded level"""
    t,y,ref,lvl,noi=load(name)
    x=demod(y,ref,LAG)
    Ls=[];As=[]
    for L in np.unique(lvl):
        m=(lvl==L)&((t-t[lvl==L][0])>tskip)
        Ls.append(L);As.append(x[m].mean())
    return np.array(Ls),np.array(As)

def truth_from_level(lvl,Ls,As):
    # smooth monotone map commanded level -> demod DC (counts); quadratic fit through origin-ish
    p=np.polyfit(Ls,As,2)
    return np.polyval(p,lvl)

# ---------- estimators (all operate on demod signal x at 200 Hz) ----------
def lp_causal(x,fc,order=2):
    sos=sos_lp(fc,order); return signal.sosfilt(sos,x,zi=signal.sosfilt_zi(sos)*x[:200].mean())[0]

def lp_zerophase(x,fc=0.1,order=2):
    return signal.sosfiltfilt(sos_lp(fc,order),x)

def kalman(x,q,R,qfun=None,x0=None):
    """2-state (a, adot) constant-velocity KF. q = process PSD of acceleration noise (counts^2/s^3).
    qfun(k, nu, S) -> multiplier on q (adaptive)."""
    n=len(x); a=np.zeros(n); P=np.array([[10.,0],[0,1.]])
    s=np.array([x[:200].mean() if x0 is None else x0,0.0])
    F=np.array([[1,DT],[0,1]]); H=np.array([1.,0.])
    Q0=np.array([[DT**3/3,DT**2/2],[DT**2/2,DT]])
    qs=np.zeros(n)
    for k in range(n):
        qm=1.0 if qfun is None else qfun.step()
        Q=Q0*q*qm
        s=F@s; P=F@P@F.T+Q
        nu=x[k]-s[0]; S=P[0,0]+R
        if qfun is not None: qfun.update(nu,S)
        K=P@H/S
        s=s+K*nu; P=P-np.outer(K,H@P)
        a[k]=s[0]; qs[k]=qm
    return a,qs

class AdaptQ:
    """raise q when the smoothed innovation is persistently biased (signal changed), relax otherwise.
    z = |EMA(nu)| / sigma_nu0 ; multiplier = exp(log(qmax_ratio)*clip((z-z0)/(z1-z0),0,1)) ; fast attack, slowdecay"""
    def __init__(self,sig0,tau_e=0.4,z0=1.0,z1=4.0,ratio=300.,tau_dec=1.0):
        self.sig0=sig0;self.ae=DT/tau_e;self.z0=z0;self.z1=z1;self.ratio=ratio;self.ad=DT/tau_dec
        self.e=0.0;self.m=1.0;self.lm=0.0
    def update(self,nu,S):
        self.e+=self.ae*(nu-self.e)
        z=abs(self.e)/self.sig0
        target=np.log(self.ratio)*min(max((z-self.z0)/(self.z1-self.z0),0),1)
        if target>self.lm: self.lm=target           # attack immediately
        else: self.lm+=self.ad*(target-self.lm)      # decay slowly
        self.m=np.exp(self.lm)
    def step(self): return self.m

# ---------- Rauch-Tung-Striebel smoother (fixed q, non-causal) ----------
def rts(x,q,R):
    n=len(x); F=np.array([[1,DT],[0,1.]]); H=np.array([1.,0]); Q=q*np.array([[DT**3/3,DT**2/2],[DT**2/2,DT]])
    s=np.array([x[:200].mean(),0.]); P=np.diag([10.,1.])
    sp=np.zeros((n,2));Pp=np.zeros((n,2,2));sf=np.zeros((n,2));Pf=np.zeros((n,2,2))
    for k in range(n):
        s=F@s;P=F@P@F.T+Q; sp[k]=s;Pp[k]=P
        S=P[0,0]+R;K=P@H/S; s=s+K*(x[k]-s[0]); P=P-np.outer(K,H@P); sf[k]=s;Pf[k]=P
    ss=sf.copy()
    for k in range(n-2,-1,-1):
        M=Pp[k+1]; det=M[0,0]*M[1,1]-M[0,1]*M[1,0]; Mi=np.array([[M[1,1],-M[0,1]],[-M[1,0],M[0,0]]])/det; C=Pf[k]@F.T@Mi; ss[k]=sf[k]+C@(ss[k+1]-sp[k+1])
    return ss[:,0]
