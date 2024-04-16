# Instructions:
#   cmsRun -j FrameworkJobReport_Run1695762407_Link2_File0000000001_RECO.xml $CMSSW_BASE/src/HGCalCommissioning/SystemTestEventFilters/test/test_raw2reco.py mode=slinkfromraw slinkBOE=0x55 cbHeaderMarker=0x7f econdHeaderMarker=0x154 bePassTrough=False inputFiles=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link1_File0000000001.bin,/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link2_File0000000001.bin fedId=1,2 inputTrigFiles=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link0_File0000000001.bin output=Run1695762407_Link2_File0000000001 runNumber=1695762407 maxEvents=1000000000
# Based on
#   https://github.com/CMS-HGCAL/cmssw/blob/hgcal-condformat-HGCalNANO-13_2_0_pre3_linearity/EventFilter/HGCalRawToDigi/test/tb_raw2reco.py
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/SystemTestEventFilters/test/test_slink_source.py
import FWCore.ParameterSet.Config as cms

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
# input options:
options.register('runNumber', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('fedId', [0], VarParsing.multiplicity.list, VarParsing.varType.int,
                 "FED IDs")
options.register('inputFiles',
                 '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link1_File0000000001.bin',
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input DAQ link file")
options.register('inputTrigFiles',
                 '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link0_File0000000001.bin',
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
options.register('dumpFRD', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also dump the FEDRawData content")
options.register('storeRAWOutput', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also store the RAW output into a streamer file")
# geometry options:
options.register('geometry', 'Extended2026D94', VarParsing.multiplicity.singleton, VarParsing.varType.string, 'geometry to use')
options.register('modules',"",mytype=VarParsing.varType.string,
                 info="Path to module mapper. Absolute, or relative to CMSSW src directory")
options.register('sicells','Geometry/HGCalMapping/data/CellMaps/WaferCellMapTraces.txt',mytype=VarParsing.varType.string,
                 info="Path to Si cell mapper. Absolute, or relative to CMSSW src directory")
options.register('sipmcells','Geometry/HGCalMapping/data/CellMaps/channels_sipmontile.hgcal.txt',mytype=VarParsing.varType.string,
                 info="Path to SiPM-on-tile cell mapper. Absolute, or relative to CMSSW src directory")
# RAW -> DIGI options:
options.register('mode', 'trivial', VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "type of emulation")
options.register('slinkBOE', 0x2a, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Begin of event marker for S-link")
options.register('cbHeaderMarker', 0x5f, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Begin of event marker for BE/capture block")
options.register('econdHeaderMarker', 0x154, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Begin of event marker for ECON-D")
options.register('bePassTrough', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "Ignore ECON-D packet mismatches") # patch unpacker behavior to deal with firmware known features
# module calibration & configurations:
options.register('params',"",mytype=VarParsing.varType.string,
                 info="Path to calibration parameters (JSON format)")
options.register('gpu', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run on GPUs")
# verbosity options:
options.register('debug', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "debugging mode")
options.parseArguments()

# DEFAULTS
if not options.params:
  outdir = os.path.join(os.environ.get('CMSSW_BASE',''),"src/HGCalCommissioning/LocalCalibration/data")
  #options.params = f"{outdir}/calibration_parameters_v2.json"
  options.params = f"{outdir}/level0_calib_params.json"
if not options.modules:
  # git clone https://github.com/pfs/Geometry-HGCalMapping.git $CMSSW_BASE/src/Geometry/HGCalMapping/data
  # TODO: move to https://gitlab.cern.ch/hgcal-dpg/hgcal-comm
  #options.modules = "Geometry/HGCalMapping/data/ModuleMaps/modulelocator_test.txt" # test beam
  options.modules = "Geometry/HGCalMapping/data/ModuleMaps/modulelocator_test_2mods.txt" # only first two modules
print(f">>> fedIds:       {options.fedId!r}")
print(f">>> Input files:  {options.inputFiles!r}")
print(f">>> Module map:   {options.modules!r}")
print(f">>> SiCell map:   {options.sicells!r}")
print(f">>> SipmCell map: {options.sipmcells!r}")
print(f">>> Calib params: {options.params!r}")

# PROCESS
from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9 as Era_Phase2
process = cms.Process('TestHGCalRecHitESProducers',Era_Phase2)

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

# INPUT
#print(">>> Prepare inputs...")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.source = cms.Source(
  "HGCalSlinkFromRawSource",
  fedIds=cms.untracked.vuint32(*options.fedId),
  inputs=cms.untracked.vstring(*options.inputFiles),
  trig_inputs=cms.untracked.vstring(*options.inputTrigFiles),
  firstRun=cms.untracked.uint32(options.runNumber),
  firstLuminosityBlockForEachRun=cms.untracked.VLuminosityBlockID(cms.LuminosityBlockID(1, 0)),
  fileNames=cms.untracked.vstring(*options.inputFiles),
)

# GEOMETRY & INDEXING
#print(">>> Prepare geometry...")
process.load(f"Configuration.Geometry.Geometry{options.geometry}Reco_cff")
process.load(f"Configuration.Geometry.Geometry{options.geometry}_cff")
process.load('Geometry.HGCalMapping.hgCalMappingIndexESSource_cfi')
process.hgCalMappingIndexESSource.modules = cms.FileInPath(options.modules)
process.hgCalMappingIndexESSource.si = cms.FileInPath(options.sicells)
process.hgCalMappingIndexESSource.sipm = cms.FileInPath(options.sipmcells)

# CALIBRATIONS & CONFIGURATION Alpaka ESProducers (for DIGI -> RECO step)
#print(">>> Prepare calibrations & configuration...")
process.load('Configuration.StandardSequences.Accelerators_cff')
#process.load('HeterogeneousCore.AlpakaCore.ProcessAcceleratorAlpaka_cfi')
#process.load('HeterogeneousCore.CUDACore.ProcessAcceleratorCUDA_cfi')
process.hgcalConfigESProducer = cms.ESProducer( # ESProducer to load configurations parameters from YAML file, like gain
  'hgcalrechit::HGCalConfigurationESProducer@alpaka',
  gain=cms.int32(1), # to switch between 80, 160, 320 fC calibration
  charMode=cms.int32(1),
  moduleIndexerSource=cms.ESInputTag('')
)
process.hgcalCalibESProducer = cms.ESProducer( # ESProducer to load calibration parameters from JSON file, like pedestals
  'hgcalrechit::HGCalCalibrationESProducer@alpaka',
  filename=cms.string(options.params), # to be set up in configTBConditions
  moduleIndexerSource=cms.ESInputTag('')
)

# RAW -> DIGI producer
#print(">>> Prepare RAW -> DIGI...")
process.load('EventFilter.HGCalRawToDigi.hgcalDigis_cfi')
process.hgcalDigis.src = cms.InputTag('HGCalSlinkFromRawSource', 'hgcalFEDRawData')
#process.hgcalDigis.src = cms.InputTag('source')
process.hgcalDigis.fedIds = cms.vuint32(*options.fedId)
process.hgcalDigis.configSource = cms.ESInputTag('')  # for HGCalConfigESSourceFromYAML
process.hgcalDigis.moduleInfoSource = cms.ESInputTag('')  # for HGCalModuleInfoESSource
process.hgcalDigis.slinkBOE = cms.uint32(options.slinkBOE) # TODO: Izaak move to config
#process.hgcalDigis.cbHeaderMarker = cms.uint32(options.cbHeaderMarker) # TODO: ask Huilin, Izaak move to config
process.hgcalDigis.econdHeaderMarker = cms.uint32(options.econdHeaderMarker) # TODO: Izaak move to config
process.hgcalDigis.bePassTrough = options.bePassTrough # TODO: Izaak move to config

## FILTER empty events
#process.load('EventFilter.HGCalRawToDigi.hgCalEmptyEventFilter_cfi')
#process.hgCalEmptyEventFilter.src = process.hgcalDigis.src
#process.hgCalEmptyEventFilter.fedIds = process.hgcalDigis.fedIds

# DIGI -> RECO producer
#print(">>> Prepare DIGI -> RECO...")
process.load('Configuration.StandardSequences.Accelerators_cff')
process.load('HeterogeneousCore.AlpakaCore.ProcessAcceleratorAlpaka_cfi')
process.load('HeterogeneousCore.CUDACore.ProcessAcceleratorCUDA_cfi')
if options.gpu:
  process.hgcalRecHit = cms.EDProducer(
    'alpaka_cuda_async::HGCalRecHitProducer',
    digis=cms.InputTag('hgcalDigis', '', 'TEST'),
    calibSource=cms.ESInputTag(''), #('hgcalCalibESProducer', ''),
    configSource=cms.ESInputTag(''), #('hgcalConfigESProducer', ''),
    n_hits_scale=cms.int32(1),
    n_blocks=cms.int32(4096),
    n_threads=cms.int32(1024)
  )
else:
  process.hgcalRecHit = cms.EDProducer(
    'alpaka_serial_sync::HGCalRecHitProducer',
    digis=cms.InputTag('hgcalDigis', '', 'TEST'),
    calibSource=cms.ESInputTag(''), #('hgcalCalibESProducer', ''),
    configSource=cms.ESInputTag(''), #('hgcalConfigESProducer', ''),
    n_hits_scale=cms.int32(1),
    n_blocks=cms.int32(1024),
    n_threads=cms.int32(4096)
  )

# MAIN PROCESSES
#print(">>> Prepare process...")
process.p = cms.Path(
  #*process.hgCalEmptyEventFilter       # FILTER empty events
  process.hgcalDigis                    # RAW -> DIGI
  #*process.hgcalRecHit                 # DIGI -> RECO (RecHit calibrations)
  #*process.hgCalRecHitsFromSoAproducer # RECO -> NANO Phase I format translator
)

# DUMP FED
if options.dumpFRD:
  #print(">>> Adding dumpFRD...")
  process.dump = cms.EDAnalyzer(
    "DumpFEDRawDataProduct",
    #label=cms.untracked.InputTag('source'),
    label=cms.untracked.InputTag('HGCalSlinkFromRawSource', 'hgcalFEDRawData'),
    feds=cms.untracked.vint32(*options.fedId),
    dumpPayload=cms.untracked.bool(True)
  )
  process.p *= process.dump

# OUTPUT
process.outpath = cms.EndPath()
if options.storeRAWOutput:
  process.outputRAW = cms.OutputModule(
    "FRDOutputModule",
    fileName=cms.untracked.string(options.output),
    source=cms.InputTag('source'),
    frdVersion=cms.untracked.uint32(6),
    frdFileVersion=cms.untracked.uint32(1),
  )
  process.outpath += process.outputRAW
