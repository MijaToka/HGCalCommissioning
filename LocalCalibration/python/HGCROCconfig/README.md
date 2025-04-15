
# Description
This set of classes allow the generation of a HGCROC configuration (yaml) from the output of the dpg analysis (json).

# Usage
Example:
```
from HGCROCInterface import HGCROCInterface
Pmanager = HGCROCInterface(Typecode="ML-F", ChannelMapFile="WaferCellMapTraces.txt", ParamMapFile="ParametersMap.json")
```
In order to instantiate a HGCROCinterface three arguments are needed:
 1. WaferCellMapTraces.txt to properly manage the channel indexing of the different module types
 2. Typecode to define the module type, as it appears in WaferCellMapTraces.txt. This is needed to use the proper channel indexing.
 3. ParametersMap.json to define how the analysis parameters map onto the HGCROC configuration

No changes or costumizations are needed for WaferCellMapTraces.txt. Instead, each parameter to be processed should be defined in ParametersMap.json or it will be ignored (see Structure of ParametersMap).

The dpg analysis json can be loaded as:
```
#each analysis json contains parameters for all the analyzed modules
with open("level0_calib_Relay1726225188.json","r") as f:
    Params = json.load(f)
    for modulename, pvals in Params.items():
        Pmanagers[modulename] = HGCROCInterface("ML-F")
        Pmanagers[modulename].from_dict(pvals)
```

## Structure of ParametersMap.json.
The file consist in the map, an example item is:
```
"Noise":{                                                                                                                                     
   "Type":"HALFwise",                                                                                                                        
   "Path":"DigitalHalf/<HALF>/Adc_TH",                                                                                                       
   "ReductionMethod":"GetNoiseThreshold",
   "ReductionMethodArgs":{
	    "Nstddev":10.0
   }
}, 
```
where:
 * The key must be exactly the analysis parameter as appears in the json file
 * "Type" defines the granularity of the parameter, it can be "CHIPwise", "HALFwise", or "CHANNELwise"
 * "Path" specifies the tree stricture of the parameter in the HGCROC configuration file
 * "ReductionMethod" specifies how to calculate half- or chip-wise parameters starting from the channel values provided by the analysis json (see Custom reduction method for more details). The parameter is optional, by default the program will take the average over the half or chip.
 * "ReductionMethodArgs" specifies possible additional arguments to provide as input to the reduction function. Depending on the definition of the reduction function in ReductionUtils.py, the parameter can be optional.      

## Custom reduction methods
Custom methods to extract a half- or chip-wise parameter from the channel values can be defined as functions in ReductionUtils.py. For example:
```
import numpy as np

#def GetNoiseThreshold(vals, Nstddev=3.0):
#    return Nstddev * np.mean(vals)

#or the less customizable version:
#def GetNoiseThreshold(vals):
#    return 3.0 * np.mean(vals)

```
In order to associate a function to a certain parameter, the value of "ReductionMethod" in ParametersMap.json should be exactly the name of the function e.g. `"ReductionMethod":"GetNoiseThreshold"`

