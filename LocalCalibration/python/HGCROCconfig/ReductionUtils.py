
import numpy as np

def GetNoiseThreshold(vals):
    return 3.0 * np.mean(vals)
