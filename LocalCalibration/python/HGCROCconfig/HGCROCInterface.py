#! /usr/bin/env python3
# Author: Fabio Monti (December 2024)
# Description: Utility to manage the dpg analysis output and produce HGCROC configuration files 



import pandas as pd
import json
import yaml
from nested_dict import nested_dict
from Parameter import ChipParameter,HalfParameter,ChannelParameter

pd.set_option('display.max_rows', 234)


class HGCROCInterface():
    def __init__(self, Typecode, ChannelMapFile="WaferCellMapTraces.txt", ParamMapFile="ParametersMap.json"):

        # load the channel map
        self.ChannelMap = pd.read_csv(ChannelMapFile, sep=' ')[["Typecode","ROC", "HalfROC", "Seq", "ROCpin", "SiCell"]]
        self.ChannelMap = self.ChannelMap[ self.ChannelMap.Typecode==Typecode ]
        self.ChannelMap["chType"]=1
        self.ChannelMap.loc[ (self.ChannelMap.ROCpin=="CALIB0") | (self.ChannelMap.ROCpin=="CALIB1") , "chType"] = 0
        self.ChannelMap.loc[ (self.ChannelMap.SiCell==-1) , "chType"] = -1
        self.ChannelMap["Channel"] = (self.ChannelMap.ROC*2 + self.ChannelMap.HalfROC)*37 + self.ChannelMap.Seq
        #print(self.ChannelMap)

        # load the parameter map
        with open(ParamMapFile,"r") as f:
            self.ParamMap = json.load(f)

        #initialize the parameter list
        self.parameters=[]

    def from_dict(self, inputdict):
        Params = pd.DataFrame.from_dict(inputdict)
        pnames = [ name for name in Params if name!="Channel"]
        Params = pd.merge(Params, self.ChannelMap, on="Channel")
        #print(Params)
        ROCs = Params.ROC.unique()
        for p in pnames:
            if p=="Channel": continue
            if not (p in self.ParamMap.keys()):
                #raise KeyError(f"Parameter {p} can not be found in the parameter map")
                print(f"WARNING: parameter {p} not defined in parameter map --> we will skip it")
                continue

            paramtype = self.ParamMap[p]["Type"]
            parampath = self.ParamMap[p]["Path"]
            paramreducmetd = None
            if "ReductionMethod" in self.ParamMap[p]:
                paramreducmetd = self.ParamMap[p]["ReductionMethod"]

            if paramtype=="CHIPwise":
                paramvalues = Params.groupby('ROC')[p]
                chip_param = ChipParameter(name=p, path=parampath, grouped_values=paramvalues, reduction_method=paramreducmetd)
                self.parameters.append(chip_param)

            elif paramtype=="HALFwise":
                paramvalues = Params.groupby(['ROC','HalfROC'])[p]
                half_param = HalfParameter(name=p, path=parampath, grouped_values=paramvalues, reduction_method=paramreducmetd)
                self.parameters.append(half_param)
                
            elif paramtype=="CHANNELwise":
                paramvalues = Params.groupby(['ROC','Channel','chType'])[p]
                ch_param = ChannelParameter(name=p, path=parampath, grouped_values=paramvalues)
                self.parameters.append(ch_param)

            else:
                raise RuntimeError(f"Unknown parameter type {paramtype}")

    def to_yaml(self, outpath, label):
        nestedConf = nested_dict()
        for p in self.parameters:
            p.dump_to_yaml(nestedConf)
        nestedConf = nestedConf.to_dict()
        #print(nestedConf)
        for ROC,cfg in nestedConf.items():
            with open(f"{outpath}/{label}_ROC{ROC}.yaml","w") as outfile:
                yaml.dump(cfg,outfile)
        
            
            
