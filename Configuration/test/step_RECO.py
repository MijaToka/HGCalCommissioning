import FWCore.ParameterSet.Config as cms

from HGCalCommissioning.Configuration.configure_sysval_reco_cff import *

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.output = 'RECO.root'
setArgParserForRECO(options)
options.parseArguments()

# get the configuration for this era
from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RECO', era=options.era, run=options.run, maxEvents=options.maxEvents, calibfile=options.calibfile)
print(f'Starting RECO with era={options.era} run={options.run}')
print(eraConfig)

# SOURCE
process.source = cms.Source("PoolSource",
   fileNames = cms.untracked.vstring(*options.files),
   secondaryFileNames = cms.untracked.vstring()
)

# RECO
process = configureRECOStep(process,options)
process.p = cms.Path(process.reco_task)

# OUTPUT
process.output = cms.OutputModule(
  "PoolOutputModule",
  fileName=cms.untracked.string(options.output),
  outputCommands=cms.untracked.vstring(
    'keep *',
    'drop FEDRawDataCollection_*_*_*',
  ),
  SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('p'))
)
process.outpath = cms.EndPath(process.output)
