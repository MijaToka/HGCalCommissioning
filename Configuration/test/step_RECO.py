import FWCore.ParameterSet.Config as cms

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.register('era', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "reconstruction era")
options.register('run', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('gpu', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run on GPUs")
options.parseArguments()

# get the configuration for this era
era = options.era
run = options.run
print(f'Starting RECO with era={era} run={run}')
from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RECO', era=era, run=run, maxEvents=options.maxEvents)
    
# SOURCE
process.source = cms.Source("PoolSource",
   fileNames = cms.untracked.vstring(*options.files),
   secondaryFileNames = cms.untracked.vstring()
)

#DIGI -> RECO
process.load('HeterogeneousCore.AlpakaCore.ProcessAcceleratorAlpaka_cfi')
process.load('HeterogeneousCore.CUDACore.ProcessAcceleratorCUDA_cfi')
if options.gpu:
    process.hgcalRecHits = cms.EDProducer(
        'alpaka_cuda_async::HGCalRecHitsProducer',
        digis=cms.InputTag('hgcalDigis', ''),
        calibSource=cms.ESInputTag('hgcalCalibParamESProducer', ''),
        configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
        n_hits_scale=cms.int32(1),
        n_blocks=cms.int32(4096),
        n_threads=cms.int32(1024)
    )
else:
    process.hgcalRecHits = cms.EDProducer(
        'alpaka_serial_sync::HGCalRecHitsProducer',
        digis=cms.InputTag('hgcalDigis', ''),
        calibSource=cms.ESInputTag('hgcalCalibParamESProducer', ''),
        configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
        n_hits_scale=cms.int32(1),
        n_blocks=cms.int32(1024),
        n_threads=cms.int32(4096)
    )
    
process.p = cms.Path(
    process.hgcalRecHits
)

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
