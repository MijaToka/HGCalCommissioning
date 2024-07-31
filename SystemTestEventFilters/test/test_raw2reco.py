# Instructions:
#   cmsRun -j FrameworkJobReport_Run1695762407_Link2_File0000000001_RECO.xml $CMSSW_BASE/src/HGCalCommissioning/SystemTestEventFilters/test/test_raw2reco.py mode=slinkfromraw slinkHeaderMarker=0x55 cbHeaderMarker=0x7f econdHeaderMarker=0x154 mismatchPassthrough=False inputFiles=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link1_File0000000001.bin,/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link2_File0000000001.bin fedId=1,2 inputTrigFiles=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link0_File0000000001.bin output=Run1695762407_Link2_File0000000001 runNumber=1695762407 maxEvents=1000000000
# Based on
#   https://github.com/CMS-HGCAL/cmssw/blob/hgcal-condformat-HGCalNANO-13_2_0_pre3_linearity/EventFilter/HGCalRawToDigi/test/tb_raw2reco.py
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/SystemTestEventFilters/test/test_slink_source.py
import FWCore.ParameterSet.Config as cms

# DEFAULT
import os
datadir = os.path.join(os.environ.get('CMSSW_BASE',''),"src/HGCalCommissioning/LocalCalibration/data")

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
# input options (BIN -> RAW):
options.register('runNumber', 1695762407, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('maxEventsPerLumiSection', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Break in lumi sections using this event count")
options.register('fedId', [0], VarParsing.multiplicity.list, VarParsing.varType.int,
                 "FED IDs")
options.register('inputFiles',
                 '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/HgcalLabtestSerenity/Relay1710429303/Run1710429303_Link1_File0000000000.bin',
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input DAQ link file")
options.register('inputTrigFiles', '',
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
###options.register('trigSeparator', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
###                 "Override default trigger packet separator (e.g. 0xcafecafe)")
# geometry options:
options.register('geometry', 'Extended2026D94', VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 'geometry to use')
options.register('modules',"HGCalCommissioning/SystemTestEventFilters/data/ModuleMaps/modulelocator_B27v1.txt",mytype=VarParsing.varType.string,
                 info="Path to module mapper. Absolute, or relative to CMSSW src directory")
options.register('sicells','Geometry/HGCalMapping/data/CellMaps/WaferCellMapTraces.txt',mytype=VarParsing.varType.string,
                 info="Path to Si cell mapper. Absolute, or relative to CMSSW src directory")
options.register('sipmcells','Geometry/HGCalMapping/data/CellMaps/channels_sipmontile.hgcal.txt',mytype=VarParsing.varType.string,
                 info="Path to SiPM-on-tile cell mapper. Absolute, or relative to CMSSW src directory")
# unpacker options (RAW -> DIGI):
###options.register('mode', 'trivial', VarParsing.multiplicity.singleton, VarParsing.varType.string,
###                 "type of emulation")
options.register('slinkHeaderMarker', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Override begin of event marker for S-link (e.g. 0x55)")
options.register('cbHeaderMarker', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Override begin of event marker for BE/capture block (e.g. 0x7f)")
options.register('econdHeaderMarker', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Override begin of event marker for ECON-D (e.g. 0x154)")
options.register('mismatchPassthrough', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Override ignore ECON-D packet mismatches") # patch unpacker behavior to deal with firmware known features
# module calibration & configurations:
options.register('fedconfig',f"{datadir}/config_feds_B27v1.json",mytype=VarParsing.varType.string,
                 info="Path to configuration (JSON format)")
options.register('modconfig',f"{datadir}/config_econds_B27v1.json",mytype=VarParsing.varType.string,
                 info="Path to configuration (JSON format)")
options.register('params',f"{datadir}/level0_calib_params_B27v1.json",mytype=VarParsing.varType.string,
                 info="Path to calibration parameters (JSON format)")
options.register('gpu', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run on GPUs")
# nano options:
options.register('skipDigi', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "skip Digis for flat table")
# DQM options (DIGI -> DQM):
options.register('prescale', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "prescale for DQM (to reduce amount of output data)")
options.register('dqmOnly', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run only the DQM step")
# output options:
options.register('dumpFRD', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also dump the FEDRawData content")
options.register('storeRAWOutput', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also store the RAW output into a streamer file")
options.register('storeOutput', True, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also store the output into an EDM file")
# verbosity options:
options.register('debug', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "debugging mode")
options.parseArguments()

# DEFAULTS
if options.inputTrigFiles==[ ]: # default: use same as input files
  import re
  trigexp = re.compile(r"(Run\d+)_Link(\d+)_(File\d+\.bin)$")
  options.inputTrigFiles = [trigexp.sub(r"\1_Link0_\3",f) for f in options.inputFiles]
print(f">>> fedIds:        {options.fedId!r}")
print(f">>> Input files:   {options.inputFiles!r}")
print(f">>> Trigger files: {options.inputTrigFiles!r}")
print(f">>> Output files:  {options.output!r}")
print(f">>> Module map:    {options.modules!r}")
print(f">>> SiCell map:    {options.sicells!r}")
print(f">>> SipmCell map:  {options.sipmcells!r}")
print(f">>> Calib params:  {options.params!r}")

# PROCESS
from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9 as Era_Phase2
process = cms.Process('RAW2RECO',Era_Phase2)

# GLOBAL TAG
from Configuration.AlCa.GlobalTag import GlobalTag
process.load("Configuration.StandardSequences.Services_cff")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.EventContent.EventContent_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.GlobalTag = GlobalTag(process.GlobalTag, 'auto:phase2_realistic', '')

# MESSAGE LOGGER
process.load("FWCore.MessageService.MessageLogger_cfi")
process.MessageLogger.cerr.FwkReport.reportEvery = 50000
if options.debug:
  process.MessageLogger.cerr.threshold = 'DEBUG'
  process.MessageLogger.debugModules = options.debugModules  # default: ['*']
  process.MessageLogger.cerr.DEBUG = cms.untracked.PSet(
    limit=cms.untracked.int32(-1)
  )
process.options.wantSummary = cms.untracked.bool(True)

# INPUT (BIN -> RAW)
#print(">>> Prepare inputs...")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.source = cms.Source(
  "HGCalSlinkFromRawSource",
  isRealData=cms.untracked.bool(True),
  runNumber=cms.untracked.uint32(options.runNumber),
  firstLumiSection=cms.untracked.uint32(1),
  maxEventsPerLumiSection=cms.untracked.int32(options.maxEventsPerLumiSection),
  useL1EventID=cms.untracked.bool(True),
  fedIds=cms.untracked.vuint32(*options.fedId),
  inputs=cms.untracked.vstring(*options.inputFiles),
  trig_inputs=cms.untracked.vstring(*options.inputTrigFiles),
  ###trigSeparator=cms.untracked.uint32(options.trigSeparator),
)
process.rawDataCollector = cms.EDAlias(
  source=cms.VPSet(
    cms.PSet(type=cms.string('FEDRawDataCollection'))
  )
)

# GEOMETRY & INDEXING
#print(">>> Prepare geometry...")
process.load(f"Configuration.Geometry.Geometry{options.geometry}Reco_cff")
process.load(f"Configuration.Geometry.Geometry{options.geometry}_cff")
from Geometry.HGCalMapping.hgcalmapping_cff import customise_hgcalmapper
process = customise_hgcalmapper(process,
                                modules=options.modules,
                                sicells=options.sicells,
                                sipmcells=options.sipmcells)

# GLOBAL HGCAL CONFIGURATION (mostly for unpacker)
process.hgcalConfigESProducer = cms.ESSource( # ESProducer to load configurations for unpacker
  # https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/HGCalConfigurationESProducer.cc
  'HGCalConfigurationESProducer',
  fedjson=cms.string(options.fedconfig), # JSON with FED configuration parameters
  modjson=cms.string(options.modconfig), # JSON with ECON-D configuration parameters
  bePassthroughMode=cms.int32(options.mismatchPassthrough), # override: ignore mismatch
  cbHeaderMarker=cms.int32(options.cbHeaderMarker),         # override: capture block header marker
  slinkHeaderMarker=cms.int32(options.slinkHeaderMarker),   # override: S-link header marker
  econdHeaderMarker=cms.int32(options.econdHeaderMarker),   # override: ECON-D header marker
  charMode=cms.int32(1),                                    # override: characterization mode
  indexSource=cms.ESInputTag('hgCalMappingESProducer','')
)

# CALIBRATIONS & CONFIGURATION Alpaka ESProducers (for DIGI -> RECO step)
#print(">>> Prepare calibrations & configuration...")
#process.load('HeterogeneousCore.AlpakaCore.ProcessAcceleratorAlpaka_cfi')
#process.load('HeterogeneousCore.CUDACore.ProcessAcceleratorCUDA_cfi')
process.hgcalConfigParamESProducer = cms.ESProducer( # ESProducer to load configurations parameters from YAML file, like gain
  # https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitConfigurationESProducer.cc
  'hgcalrechit::HGCalConfigurationESProducer@alpaka',
  gain=cms.int32(1), # to switch between 80, 160, 320 fC calibration
  #charMode=cms.int32(1),
  indexSource=cms.ESInputTag('hgCalMappingESProducer',''),
)
process.hgcalCalibParamESProducer = cms.ESProducer( # ESProducer to load calibration parameters from JSON file, like pedestals
  # https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitCalibrationESProducer.cc
  'hgcalrechit::HGCalCalibrationESProducer@alpaka',
  filename=cms.string(options.params), # to be set up in configTBConditions
  indexSource=cms.ESInputTag('hgCalMappingESProducer',''),
  #configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
  configSource=cms.ESInputTag(''),
)
#process.hgcalCalibParamESProducer.indexSource = process.hgcalConfigESProducer.indexSource

# RAW -> DIGI producer
# https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/EventFilter/HGCalRawToDigi/plugins/HGCalRawToDigi.cc
#print(">>> Prepare RAW -> DIGI...")
process.load('EventFilter.HGCalRawToDigi.hgcalDigis_cfi')
process.hgcalDigis.src = cms.InputTag('rawDataCollector')
process.hgcalDigis.fedIds = cms.vuint32(*options.fedId)
#process.hgcalDigis.configSource = cms.ESInputTag('hgcalConfigESProducer', '') # TODO: put this back once implemented

## FILTER empty events
#process.load('EventFilter.HGCalRawToDigi.hgCalEmptyEventFilter_cfi')
#process.hgCalEmptyEventFilter.src = process.hgcalDigis.src
#process.hgCalEmptyEventFilter.fedIds = process.hgcalDigis.fedIds

# DIGI -> RECO producer
# https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitsProducer.cc
#print(">>> Prepare DIGI -> RECO...")
process.load('HeterogeneousCore.AlpakaCore.ProcessAcceleratorAlpaka_cfi')
process.load('HeterogeneousCore.CUDACore.ProcessAcceleratorCUDA_cfi')
if options.gpu:
  process.hgcalRecHits = cms.EDProducer(
    'alpaka_cuda_async::HGCalRecHitsProducer',
    digis=cms.InputTag('hgcalDigis', '', 'RAW2RECO'),
    calibSource=cms.ESInputTag('hgcalCalibParamESProducer', ''),
    configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
    n_hits_scale=cms.int32(1),
    n_blocks=cms.int32(4096),
    n_threads=cms.int32(1024)
  )
else:
  process.hgcalRecHits = cms.EDProducer(
    'alpaka_serial_sync::HGCalRecHitsProducer',
    digis=cms.InputTag('hgcalDigis', '', 'RAW2RECO'),
    calibSource=cms.ESInputTag('hgcalCalibParamESProducer', ''),
    configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
    n_hits_scale=cms.int32(1),
    n_blocks=cms.int32(1024),
    n_threads=cms.int32(4096)
  )

# NANO producer (DIGI -> NANO, RECO -> NANO)
process.load('HGCalCommissioning.NanoTools.hgCalNanoTableProducer_cfi')
process.hgcalNanoFlatTable = cms.EDProducer(
  # https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/NanoTools/plugins/HGCalNanoTableProducer.cc
  'HGCalNanoTableProducer',
  digis=cms.InputTag('hgcalDigis', '', 'RAW2RECO'),
  rechits=cms.InputTag('hgcalRecHits', '', 'RAW2RECO'),
  skipDigi=cms.bool(options.skipDigi)
)

# DEFINE PROCESSES: RAW -> DIGI -> DQM only
# https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/DQM/plugins/HGCalSysValDigisClient.cc
# https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/DQM/plugins/HGCalSysValDigisHarvester.cc
if options.dqmOnly:
  print(">>> Prepare RAW -> DIGI -> DQM processes...")
  process.load('HGCalCommissioning.DQM.hgCalSysValDigisClient_cfi')
  process.load('HGCalCommissioning.DQM.hgCalSysValDigisHarvester_cfi')
  process.hgCalSysValDigisClient.PrescaleFactor = options.prescale
  process.DQMStore = cms.Service("DQMStore")
  process.load("DQMServices.FileIO.DQMFileSaverOnline_cfi")
  process.dqmSaver.tag = 'HGCAL'
  process.dqmSaver.runNumber = 123456
  process.p = cms.Path(
    #*process.hgCalEmptyEventFilter    # FILTER empty events
    process.hgcalDigis                 # RAW -> DIGI
    *process.hgCalSysValDigisClient    # DIGI -> DQM
    *process.hgCalSysValDigisHarvester
    *process.dqmSaver
  )

# DEFINE PROCESSES: full RAW -> DIGI -> RECO -> NANO
else:
  print(">>> Prepare RAW -> DIGI -> RECO -> NANO process...")
  process.p = cms.Path(
    #*process.hgCalEmptyEventFilter       # FILTER empty events
    process.hgcalDigis                    # RAW -> DIGI
    *process.hgcalRecHits                 # DIGI -> RECO (RecHit calibrations)
    *process.hgcalNanoFlatTable           # DIGI/RECO -> NANO (flat table)
    #*process.hgCalRecHitsFromSoAproducer  # RECO -> NANO Phase I format translator
  )

# DUMP FED
if options.dumpFRD:
  process.dump = cms.EDAnalyzer(
    "DumpFEDRawDataProduct",
    label=cms.untracked.InputTag('rawDataCollector'),
    feds=cms.untracked.vint32(*options.fedId),
    dumpPayload=cms.untracked.bool(True)
  )
  process.p *= process.dump

# OUTPUT
process.outpath = cms.EndPath()
if options.storeOutput:
  process.output = cms.OutputModule(
    "PoolOutputModule",
    fileName=cms.untracked.string(options.output),
    outputCommands=cms.untracked.vstring(
        'drop *',
        'keep HGCalTestSystemMetaData_*_*_*',
        'keep FEDRawDataCollection_*_*_*',
        'keep *SoA*_hgcalDigis_*_*',
        'keep *SoA*_hgcalRecHits_*_*',
        'keep *_hgcalNanoFlatTable_*_*'
    ),
    #SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('p'))
  )
  process.outpath += process.output

# RAW OUTPUT
if options.storeRAWOutput:
  process.outputRAW = cms.OutputModule(
    "FRDOutputModule",
    fileName=cms.untracked.string(options.output),
    source=cms.InputTag('rawDataCollector'),
    frdVersion=cms.untracked.uint32(6),
    frdFileVersion=cms.untracked.uint32(1),
  )
  process.outpath += process.outputRAW
  
