import numpy as np, glob, os
D='data_20261123_0015/'
def load(name):
    d=np.genfromtxt(D+name,delimiter=',',skip_header=1)
    t=d[:,0]/1000.0; y=d[:,1]/8.0; ref=d[:,2]; lvl=d[:,3]; noi=d[:,4]
    return t,y,ref,lvl,noi
