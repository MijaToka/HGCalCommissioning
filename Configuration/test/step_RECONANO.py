import FWCore.ParameterSet.Config as cms

from HGCalCommissioning.Configuration.configure_sysval_reco_cff import *
from HGCalCommissioning.NanoTools.configure_sysval_nano_cff import *

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
setArgParserForRECO(options)
setArgParserForNANO(options, skipRecHitsDefault=False)
options.parseArguments()

from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RECONANO', era=options.era, run=options.run, maxEvents=options.maxEvents, calibfile=options.calibfile)
print(f'Era = {options.era} has the following config')
print(eraConfig)

# SOURCE
process.source = cms.Source("PoolSource",
                            fileNames = cms.untracked.vstring(*options.files),
                            secondaryFileNames = cms.untracked.vstring()
                            )

# tasks/paths to run
process = configureRECOStep(process,options)
process = configureNANOStep(process,options)
process.schedule.associate(process.reco_task)
