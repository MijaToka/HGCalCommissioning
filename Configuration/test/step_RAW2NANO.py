import FWCore.ParameterSet.Config as cms

from HGCalCommissioning.SystemTestEventFilters.configure_sysval_raw2digi_cff import *
from HGCalCommissioning.NanoTools.configure_sysval_nano_cff import *

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
setArgParserForRAW2DIGI(options)
setArgParserForNANO(options, skipRecHitsDefault=True)
options.parseArguments()

from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RAW2NANO', era=options.era, run=options.run, maxEvents=options.maxEvents)
print(f'Era = {options.era} has the following config')
print(eraConfig)

process = configureRAW2DIGIStep(process,options,eraConfig)
process = configureNANOStep(process,options)
process.schedule.insert(0, process.raw2digi_step)
