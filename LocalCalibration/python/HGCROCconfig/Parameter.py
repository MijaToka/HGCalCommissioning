#! /usr/bin/env python3
# Author: Fabio Monti (December 2024)
# Description: Utility to manage HGCROC parameters

def edit_key(key, half=None, channel=None, chType=None):
    # the parameter map has special keywords to identify each half in the path
    chtypestr=""
    if not(chType is None):
        if (chType==1) or (chType==-1): # connected or nonconnected channel
            chtypestr="ch"
        elif chType==0: # calibration channel
            chtypestr="calib"
        elif chType==2: # common mode
            chtypestr="cm"
        else:
            raise ValueError("Unknown channel type")
    mod_key = key.replace("<HALF>",str(half))\
                 .replace("<CHTYPE>",chtypestr)\
                 .replace("<CH>",str(channel))
    if mod_key.isnumeric():
        mod_key = int(mod_key)
    return mod_key
    



class ChipParameter():
    def __init__(self, name, path, grouped_values, reduction_method=None, reduction_method_args={}):
        self.name=name
        self.path=path.split('/')
        self.values={}
        # Check that the parameter has the same value for all channels within the same roc
        # and save parameter in memory
        for chip,paramvalues in grouped_values:

            if not (reduction_method is None):
                import ReductionUtils
                reduction_function = getattr(ReductionUtils, reduction_method)
                v = reduction_function(paramvalues, **reduction_method_args)
            
            else:
                if len(paramvalues.unique())>1:
                    print(f"WARNING: parameter {name} has different values within ROC {chip} --> we will take the average value over the chip")
                v = paramvalues.mean()

            self.values[chip] = int(round(v))
            
    def dump_to_yaml(self, nestedConf):
        for chip, paramval in self.values.items():
            cfg = nestedConf[chip]
            for d in self.path[:-1]:
                mod_d=d
                if mod_d.isnumeric():
                    mod_d = int(mod_d)
                cfg = cfg[mod_d]
            cfg[self.path[-1]] = paramval

            
class HalfParameter():
    def __init__(self, name, path, grouped_values, reduction_method=None, reduction_method_args={}):
        self.name=name
        self.path=path.split('/')
        self.values={}
        # Check that the parameter has the same value for all channels within the same roc,half
        # and save parameter in memory 
        for (chip,half),paramvalues in grouped_values:
            if not (reduction_method is None):
                import ReductionUtils
                reduction_function = getattr(ReductionUtils, reduction_method)
                v = reduction_function(paramvalues, **reduction_method_args)
            else:
                if len(paramvalues.unique())>1:
                    print(f"WARNING: parameter {name} has different values within ROC {chip} --> we will take the average value over the chip")
                v = paramvalues.mean()
            self.values[(chip,half)] = int(round(v))
            
    def dump_to_yaml(self, nestedConf):
        for (chip,half), paramval in self.values.items():
            cfg = nestedConf[chip]
            for d in self.path[:-1]:
                mod_d = edit_key(d, half=half)
                cfg = cfg[mod_d]
            mod_d=edit_key(self.path[-1], half=half)
            cfg[mod_d] = paramval

            
class ChannelParameter():
    def __init__(self, name, path, grouped_values):
        self.name=name
        self.path=path.split('/')
        self.values={}
        # Check that the parameter has the same value for all channels within the same roc,channel
        # and save parameter in memory
        for (chip,channel,chType),paramvalues in grouped_values:
            if len(paramvalues.unique())>1:
                raise ValueError(f"Parameter {name} takes multiple values in (ROC,channel,chType)=({chip},{channel},{chType})")
            v = paramvalues.mean()
            self.values[(chip,channel,chType)] = int(round(v))

    def dump_to_yaml(self, nestedConf):
        for (chip,channel,chType), paramval in self.values.items():
            cfg = nestedConf[chip]
            # the parameter map has special keywords to identify each channel and channel type in the path
            for d in self.path[:-1]:
                mod_d = edit_key(d, channel=channel, chType=chType)
                cfg = cfg[mod_d]
            mod_d=edit_key(self.path[-1], channel=channel, chType=chType)
            cfg[mod_d] = paramval
            
        
