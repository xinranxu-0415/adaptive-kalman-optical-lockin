from pathlib import Path
import hashlib, json
import numpy as np
from pipe import kalman,kalman_numpy,AdaptQ,demod,LAG
from load import load,DATA
ROOT=Path(__file__).resolve().parents[1]
audit=[]
for f in sorted(DATA.glob('*.csv')):
    d=np.genfromtxt(f,delimiter=',',skip_header=1)
    assert d.shape[1]==5 and np.isfinite(d).all()
    assert len(d)==(18000 if 'run_K_' in f.name else 12000)
    assert np.all(np.diff(d[:,0])>0)
    audit.append(dict(file=f.name,samples=len(d),median_dt_ms=float(np.median(np.diff(d[:,0]))),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
assert len(audit)==19
t,y,ref,lvl,noise=load('run_1_r1.csv'); x=demod(y,ref,LAG)
errors={}
for mode in ('fixed','adaptive'):
    def ad(): return AdaptQ(2.3,1.,2.5,3.5,5000.,3.) if mode=='adaptive' else None
    a,q=kalman(x,3e-4,196.,ad()); b,r=kalman_numpy(x,3e-4,196.,ad())
    errors[mode]=dict(amplitude_max_abs=float(np.max(abs(a-b))),q_multiplier_max_abs=float(np.max(abs(q-r))))
    np.testing.assert_allclose(a,b,rtol=1e-9,atol=1e-8)
    np.testing.assert_allclose(q,r,rtol=1e-9,atol=1e-7)
(ROOT/'results').mkdir(exist_ok=True)
(ROOT/'results/verification.json').write_text(json.dumps(dict(data=audit,optimized_vs_original=errors),indent=2))
print('PASS: all 19 recordings valid; accelerated KF agrees with original NumPy implementation.')
