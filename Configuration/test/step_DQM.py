import FWCore.ParameterSet.Config as cms

from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.register('run', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('era', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "reconstruction era")
options.parseArguments()

print(f'Starting DQM of Run={options.run} with era={options.era}')

from HGCalCommissioning.Configuration.SysValEras_cff import *
process, _ = initSysValCMSProcess(procname='DQM',era=options.era, run=options.run, maxEvents=options.maxEvents)

# SOURCE (add RAW files if they were passed)
process.source = cms.Source("PoolSource",
                            fileNames = cms.untracked.vstring(*options.files),
                            secondaryFileNames = cms.untracked.vstring(*options.secondaryFiles),
                            )

# DQM
from HGCalCommissioning.DQM.hgcalSysValDQM_cff import customizeSysValDQM
process = customizeSysValDQM(process, runNumber=options.run)
