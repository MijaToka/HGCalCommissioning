import FWCore.ParameterSet.Config as cms

from HGCalCommissioning.NanoTools.configure_sysval_nano_cff import *

from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.output='NANO.root'
setArgParserForNANO(options)
options.parseArguments()
print(f'Starting NANO with era={options.era} run={options.run} skipRecHits={options.skipRecHits}')

# SOURCE
process.source = cms.Source("PoolSource",
   fileNames = cms.untracked.vstring(*options.files),
   secondaryFileNames = cms.untracked.vstring(*options.secondaryFiles)
)

# NANO
process = configureNANOStep(process,options)

