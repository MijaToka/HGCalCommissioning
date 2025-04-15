import FWCore.ParameterSet.Config as cms

from HGCalCommissioning.SystemTestEventFilters.configure_sysval_raw2digi_cff import *

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.output = 'RAW2DIGI.root'
setArgParserForRAW2DIGI(options)
options.parseArguments()

from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RAW2DIGI', era=options.era, run=options.run, maxEvents=options.maxEvents)
print(f'Era = {options.era} has the following config')
print(eraConfig)

process = configureRAW2DIGIStep(process,options,eraConfig)

process.output = cms.OutputModule(
  "PoolOutputModule",
  fileName=cms.untracked.string(options.output),
  outputCommands=cms.untracked.vstring(
    'drop *',
    'keep HGCalTestSystemMetaData_*_*_*',
    'keep FEDRawDataCollection_*_*_*',
    'keep *SoA*_hgcalDigis_*_*',
  ),
  SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('raw2digi_step'))
)
if options.enableTPGunpacker:
    process.output.outputCommands.extend( ['keep TrgFEDRawDataCollection_*_*_*'] )

process.outpath = cms.EndPath(process.output)
