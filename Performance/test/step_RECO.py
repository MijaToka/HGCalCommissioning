# Author: Izaak Neutelings (January 2025)
# Source: HGCalCommissioning/Configuration/test/step_RECO.py
# Instructions: Adding ThroughputService to measure performance
import FWCore.ParameterSet.Config as cms

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.register('era', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "reconstruction era")
options.register('run', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('nthreads', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "number of nthreads")
options.register('scaleFEDs', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "naively scale data by copying FED data")
options.register('logtag', "", VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "tag for ThroughputService log")
options.register('gpu', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run on GPUs")
options.parseArguments()

# USER SETTINGS
era      = options.era
run      = options.run
nthreads = options.nthreads
scale    = options.scaleFEDs

# GET COMMON CONFIG
print(f'Starting RECO with era={era} run={run}')
from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RECO', era=era, run=run, maxEvents=options.maxEvents, nthreads=nthreads)
print(f">>> Era = {era} has the following config:")
print(f">>>   eraConfig  = {eraConfig}")
print(f">>>   inputFiles = {options.files}")
print(f">>>   nthreads   = {process.options.numberOfThreads}")
print(f">>>   nstreams   = {process.options.numberOfStreams}")

# SCALE
from HGCalCommissioning.Performance.utils import *
if scale>=2: # assume options.files already contains scaled DIGIs
  assert all(f"_scale{scale}" in f for f in options.files)
  scaleFEDs(process,None,eraConfig,scale=scale,verb=1)

# MEASURE PERFORMANCE
logtag = f"_RECO_scale{scale}_nthread{nthreads}{options.logtag}"
#addFastTimerService(process,logtag=logtag)
addThroughoutService(process,options,logtag=logtag)

# SOURCE
process.source = cms.Source("PoolSource",
   fileNames = cms.untracked.vstring(*options.files),
   secondaryFileNames = cms.untracked.vstring()
)

# INPUT ONLY
if '_onlyin' in logtag: # force reading of input data with GenericConsumer
  process.consumer = cms.EDAnalyzer("GenericConsumer",
      eventProducts = cms.untracked.vstring('128falsehgcaldigiHGCalDigiSoALayoutPortableHostCollection_hgcalDigis__RAW2DIGI')
  )
  process.p = cms.Path(
      process.consumer
  )

# INPUT + DIGI -> RECO
else:
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
  
  # OUTPUT
  if '_noout' in logtag: # no output file, just a consumer to read output data
      #print('here')
      process.consumer = cms.EDAnalyzer("GenericConsumer",
          eventProducts = cms.untracked.vstring('hgcalRecHits')
      )
      process.p = cms.Path(
          process.hgcalRecHits
          *process.consumer # probably not needed in this case?
      )
  else: # output file
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
  
