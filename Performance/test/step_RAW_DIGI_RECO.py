# Author: Izaak Neutelings (January 2025)
# Source: HGCalCommissioning/Configuration/test/step_RAW2DIGI.py
# Instructions: Adding ThroughputService to measure performance
import FWCore.ParameterSet.Config as cms

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.register('run', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('lumi', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "first lumi section")
options.register('era', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "reconstruction era")
options.register('nthreads', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "number of nthreads")
options.register('logtag', "", VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "tag for ThroughputService log")
options.register('fromFEDRaw', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "start from FEDRawDataCollection (skip raw binary)")
options.register('scaleFEDs', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "naively scale data by copying FED data")
options.register('inputTrigFiles', [],
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
options.register('gpu', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run on GPUs")
options.parseArguments()

# USER SETTINGS
import json
run = options.run
lumi = options.lumi
era = options.era
nthreads = options.nthreads
scale = options.scaleFEDs
fromFEDRaw = options.fromFEDRaw
inputFiles = options.files
inputTrigFiles = options.inputTrigFiles
if len(inputFiles) != len(inputTrigFiles) and not fromFEDRaw:
    raise ValueError('Number of input files does not match trigger files!!!')
if len(inputFiles) < 0:
    raise ValueError('Missing input files')
print(f'Starting RAW2DIGI of Run={run} Lumi={lumi} with era={era}')
print(f'\t files={inputFiles}')
print(f'\t trigfiles={inputTrigFiles}')

# GET COMMON CONFIG
from HGCalCommissioning.Configuration.SysValEras_cff import *
procname = 'FEDRAWDIGIRECO' if fromFEDRaw else 'RAWDIGIRECO'
process, eraConfig = initSysValCMSProcess(procname=procname, era=era, run=run,
                                          maxEvents=options.maxEvents, nthreads=nthreads)
print(f">>> Era = {era} has the following config:")
print(f">>>   eraConfig  = {eraConfig}")
print(f">>>   inputFiles = {inputFiles}")
print(f">>>   nthreads   = {process.options.numberOfThreads}")
print(f">>>   nstreams   = {process.options.numberOfStreams}")

# SCALE
from HGCalCommissioning.Performance.utils import *
import copy
origFedIds = copy.deepcopy(eraConfig['fedId'])
if scale >= 2:
    inputFiles = scaleFEDs(process, inputFiles, eraConfig, scale=scale, verb=1)

# MEASURE PERFORMANCE
logtag = f"_{procname}_scale{scale}_nthread{nthreads}{options.logtag}"
# addFastTimerService(process,logtag=logtag)
addThroughoutService(process, options, logtag=logtag)

# INPUT: BIN -> RAW
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.options.wantSummary = cms.untracked.bool(True)
if not fromFEDRaw:  # read binary with HGCalSlinkFromRawSource
    process.source = cms.Source(
        "HGCalSlinkFromRawSource",
        isRealData=cms.untracked.bool(True),
        runNumber=cms.untracked.uint32(run),
        firstLumiSection=cms.untracked.uint32(lumi),
        maxEventsPerLumiSection=cms.untracked.int32(-1),
        useL1EventID=cms.untracked.bool(True),
        fedIds=cms.untracked.vuint32(*origFedIds),
        inputs=cms.untracked.vstring(*inputFiles),
        n_feds_scale=cms.untracked.uint32(scale),
        trig_inputs=cms.untracked.vstring(*inputTrigFiles),
        trig_num_blocks=cms.untracked.uint32(eraConfig['trig_num_blocks']),
        trig_scintillator_block_id=cms.untracked.int32(eraConfig['trig_scintillator_block'])
    )
    process.rawDataCollector = cms.EDAlias(
        source=cms.VPSet(
            cms.PSet(type=cms.string('FEDRawDataCollection'))
        )
    )

# INPUT: RAW
# start from FEDRawDataCollection (EDM format)
# i.e., skip reading binary with HGCalSlinkFromRawSource
else:
    process.source = cms.Source("PoolSource",
                                fileNames=cms.untracked.vstring(*options.files),
                                secondaryFileNames=cms.untracked.vstring()
                                )


# RAW -> DIGI producer
# Trigger: https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/merge_requests/48
process.load('EventFilter.HGCalRawToDigi.hgcalDigis_cfi')
# process.hgcalDigis = cms.EDProducer('HGCalRawToDigiTrigger')
process.hgcalDigis.src = cms.InputTag('rawDataCollector')
process.hgcalDigis.fedIds = cms.vuint32(*eraConfig['fedId'])
parallelFEDs = (nthreads >= 2 and (len(process.hgcalDigis.fedIds) >= 2 or scale >= 2))
process.hgcalDigis.doSerial = cms.bool(not parallelFEDs)  # False for parallelizing over FEDs

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
        n_threads=cms.int32(64)
    )
else:
    process.hgcalRecHits = cms.EDProducer(
        'alpaka_serial_sync::HGCalRecHitsProducer',
        digis=cms.InputTag('hgcalDigis', ''),
        calibSource=cms.ESInputTag('hgcalCalibParamESProducer', ''),
        configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
        n_hits_scale=cms.int32(1),
        n_blocks=cms.int32(1024),
        n_threads=cms.int32(64)
    )

process.p = cms.Path(
    process.hgcalDigis * process.hgcalRecHits
)

# OUTPUT
process.output = cms.OutputModule(
    "PoolOutputModule",
    fileName=cms.untracked.string(options.output),
    outputCommands=cms.untracked.vstring(
        'drop *',
        'keep HGCalTestSystemMetaData_*_*_*',
        # 'keep FEDRawDataCollection_*_*_*',
        'keep *SoA*_hgcalDigis_*_*',
        'keep *_hgcalRecHits_*_*',
    ),
    SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('p'))
)
process.outpath = cms.EndPath(process.output)
