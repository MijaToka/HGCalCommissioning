import FWCore.ParameterSet.Config as cms

from HGCalCommissioning.SystemTestEventFilters.configure_sysval_raw2digi_cff import *
from HGCalCommissioning.NanoTools.configure_sysval_nano_cff import *
from HGCalCommissioning.DQM.hgcalSysValDQM_cff import customizeSysValDQM

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
process = customizeSysValDQM(process, runNumber=options.run)
process.schedule.insert(0, process.raw2digi_step)

#DQM harvester requires max one concurrent lumi block
process.options.numberOfConcurrentLuminosityBlocks = 1
process.schedule.append(process.dqmPath)

#save edm file only if requested
import os
edmfile = options.secondaryOutput
base_edmfile_name = edmfile.replace('.root','').split('_')[0]
if len(base_edmfile_name)>0:
    print(f'RAW2DIGI EDM file will be stored as well @ {edmfile}')
    process.edmoutput = cms.OutputModule(
        "PoolOutputModule",
        fileName=cms.untracked.string(edmfile),
        outputCommands=cms.untracked.vstring(
            'drop *',
            'keep HGCalTestSystemMetaData_*_*_*',
            'keep *FEDRawDataCollection_*_*_*',
            'keep *SoA*_hgcalDigis_*_*',
        ),
        SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('raw2digi_step'))
    )
    process.edmoutpath = cms.EndPath(process.edmoutput)
    process.schedule.append( process.edmoutpath )
else:
    print('No RAW2DIGI EDM file will be stored (default behavior)')
