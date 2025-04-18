#! /usr/bin/env python3
# Author: Fabio Monti (December 2024)
# Description: Utility to manage the dpg analysis output and produce HGCROC configuration files 

import os
import pandas as pd
import json
import yaml
try:
    from nested_dict import nested_dict
except Exception as e:
    print(e)
    print('Please run python3 -m pip install nested_dict --user')
from typing import Union
from Parameter import ChipParameter,HalfParameter,ChannelParameter

pd.set_option('display.max_rows', 234)

class HGCROCInterface():
    def __init__(self, Typecode, ChannelMapFile="WaferCellMapTraces.txt", ParamMapFile="ParametersMap.json"):

        #cut away un-needed part of the typecode
        wafType = Typecode.replace('_','-')[0:4]
        
        # load the channel map
        self.ChannelMap = pd.read_csv(ChannelMapFile, sep=' ')[["Typecode","ROC", "HalfROC", "Seq", "ROCpin", "SiCell"]]
        self.ChannelMap = self.ChannelMap[ self.ChannelMap.Typecode==wafType ]  
        self.ChannelMap["chType"]=1
        self.ChannelMap.loc[ (self.ChannelMap.ROCpin=="CALIB0") | (self.ChannelMap.ROCpin=="CALIB1") , "chType"] = 0
        self.ChannelMap.loc[ (self.ChannelMap.SiCell==-1) , "chType"] = -1
        self.ChannelMap["Channel"] = (self.ChannelMap.ROC*2 + self.ChannelMap.HalfROC)*37 + self.ChannelMap.Seq
        self.ChannelMap['chTypeA'] = self.ChannelMap['chType'].abs()
        self.ChannelMap = self.ChannelMap.sort_values(by=['ROC','chTypeA','Channel'])
        self.ChannelMap["Channel0"] = self.ChannelMap.groupby(['ROC','chTypeA'],as_index=False).apply(lambda x: x.reset_index()).reset_index().set_index("level_1").index

        # load the parameter map
        with open(ParamMapFile,"r") as f:
            self.ParamMap = json.load(f)
        
        #initialize the parameter list
        self.parameters=[]

    def from_dict(self, inputdict):

        """combine channel map with the measured parameters to be mapped to the ROC config"""
        
        for p in self.ParamMap.keys():

            paramtype = self.ParamMap[p]["Type"]
            parampath = self.ParamMap[p]["Path"]
            if paramtype in ['CHIPwise','HALFwise'] and 'ierx' in inputdict:
                Params = pd.DataFrame.from_dict({k:inputdict[k] for k in ['ierx',p]})
                Params['ROC'] = Params['ierx'].floordiv(2)
                Params['HalfROC'] = Params['ierx'].mod(2)
            elif 'Channel' in inputdict:
                Params = pd.DataFrame.from_dict({k:inputdict[k] for k in ['Channel',p]})
                Params = pd.merge(Params, self.ChannelMap, on="Channel")
            paramreducmetd = None
            paramreducmetdargs = {}
            if "ReductionMethod" in self.ParamMap[p]:
                paramreducmetd = self.ParamMap[p]["ReductionMethod"]

            if "ReductionMethodArgs" in self.ParamMap[p]:
                paramreducmetdargs = self.ParamMap[p]["ReductionMethodArgs"]

            if paramtype=="CHIPwise":
                paramvalues = Params.groupby('ROC')[p]
                chip_param = ChipParameter(name=p, path=parampath, grouped_values=paramvalues,
                                           reduction_method=paramreducmetd, reduction_method_args=paramreducmetdargs)
                self.parameters.append(chip_param)

            elif paramtype=="HALFwise":
                paramvalues = Params.groupby(['ROC','HalfROC'])[p]
                half_param = HalfParameter(name=p, path=parampath, grouped_values=paramvalues,
                                           reduction_method=paramreducmetd, reduction_method_args=paramreducmetdargs)
                self.parameters.append(half_param)
                
            elif paramtype=="CHANNELwise":
                paramvalues = Params.groupby(['ROC','Channel','chType'])[p]
                ch_param = ChannelParameter(name=p, path=parampath, grouped_values=paramvalues)
                self.parameters.append(ch_param)

            elif paramtype=="CHANNEL0wise":
                paramvalues = Params.groupby(['ROC','Channel0','chType'])[p]
                ch_param = ChannelParameter(name=p, path=parampath, grouped_values=paramvalues)
                self.parameters.append(ch_param)
                
            else:
                raise RuntimeError(f"Unknown parameter type {paramtype}")

    def to_yaml(self, outpath, label):

        """put everything in the final yaml files"""
        
        nestedConf = nested_dict()
        for p in self.parameters:
            p.dump_to_yaml(nestedConf)
        
        label = label.replace('_', '-')
        nestedConf = nestedConf.to_dict()
        for ROC,cfg in nestedConf.items():
            with open(f"{outpath}/{label}_ROC{ROC}.yaml","w") as outfile:
                yaml.dump(cfg,outfile)
        

def DPGjsonToROCYaml(CalibJson : Union[dict,str], ChannelMapFile : str, ParamMapFile:str, OutPath:str):
    """loops over the typecodes in a DPG json"""

    #load the json if needed
    if type(CalibJson)==str:
        with open(CalibJson) as json_data:
            calib_dict = json.load(json_data)
    else:
        calib_dict = CalibJson

    for typecode, data in calib_dict.items():
        if typecode.startswith('MH'): # TODO: fixe me when we already swap eRx's in CMSSW
            data = swapERx(data)
        rocio = HGCROCInterface(typecode,ChannelMapFile,ParamMapFile)
        rocio.from_dict(data)
        rocio.to_yaml(OutPath,typecode)

def swapERx(data):
    """Swap eRx's in each ROC of HD modules to match front end mapping.
    TODO: Should become fixed in CMSSW's unpacker instead.
    """
    if 'Channel' in data:
        sort_idx = [i+37*((ierx+1)%2)+74*roc for roc in range(6) for ierx in range(2) for i in range(37)]
        for key in data:
             if len(data[key])!=444 or key=='Channel': continue
             data[key] = [data[key][i] for i in sort_idx]
    if 'ierx' in data:
        sort_idx = [(ierx+1)%2+2*roc for roc in range(6) for ierx in range(2)]
        for key in data:
             if len(data[key])!=12 or key=='ierx': continue
             data[key] = [data[key][i] for i in sort_idx]
    if not ('Channel' in data or 'ierx' in data):
        print(">>> HGCROCInterface.swapERx: WARNING! Could not swap eRx's for HD... No 'Channel' or 'ierx' key...")
    return data

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--waferCellMap",
                        help='wafer cell map=%(default)',
                        default="$CMSSW_DATA_PATH/data-Geometry-HGCalMapping/V00-01-00/Geometry/HGCalMapping/data/CellMaps/WaferCellMapTraces.txt", type=str)
    parser.add_argument("-p", "--paramsMap",
                        help='parameters to extract from DPG json and export to HGCROCConfig', type=str, required=True)
    parser.add_argument("-j", "--json",
                        help='json resulting fron the DPG calibration analysis',
                        type=str, required=True)
    parser.add_argument("-o", "--output",
                        default='./', help='output directory', type=str)
    args = parser.parse_args()

    args.waferCellMap = os.path.expandvars( args.waferCellMap )
    DPGjsonToROCYaml(CalibJson=args.json, ChannelMapFile=args.waferCellMap, ParamMapFile=args.paramsMap, OutPath=args.output)
