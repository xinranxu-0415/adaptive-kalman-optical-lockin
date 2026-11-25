from pathlib import Path
import numpy as np
DATA = Path(__file__).resolve().parents[1] / 'data'
def load(name):
    d = np.genfromtxt(DATA / name, delimiter=',', skip_header=1)
    return d[:,0]/1000., d[:,1]/8., d[:,2], d[:,3], d[:,4]
