
import numpy as np

def GetNoiseThreshold(vals, Nstddev=3.0):
    return Nstddev * np.mean(vals)
