# Author: Izaak Neutelings (April 2025)

def getFEChannelIndex(ich_ros, h_chType, isHD=False):
    """
    Map channel index of readout sequence used in CMSSW mapping (0-221 for LD, 0-441 for HD)
    to the channel index used in the FE configuration (0-35 for first eRx, 36-71 for second eRx):
      - not counting calibration channels;
      - swapping eRx's in HD modules. (WARNING! Check that is still the case!)
    Integrating over channel types in a TH1 (0: calibration, 1: channel, 2: common mode),
    counting each calibration channel as two.
    """
    if h_chType.GetBinContent(ich_ros+1)==0: # is calibration channel
        return -1 # does not exit in FE
    i0 = 74*(ich_ros//74) # first index in the same ROC
    ich_fe = sum(1*(h_chType.GetBinContent(i+1)!=0) for i in range(i0,ich_ros+1))-1
    if isHD: # swap eRx's
         ich_fe = (36+ich_fe) if ich_fe<36 else (ich_fe-36)
    return ich_fe
    
