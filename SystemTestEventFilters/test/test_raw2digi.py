# Instructions:
#   cmsRun $CMSSW_BASE/src/HGCalCommissioning/SystemTestEventFilters/test/test_raw2digi.py charMode=10 maxEvents=10
# Based on
#   https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/SystemTestEventFilters/test/test_raw2reco.py
import FWCore.ParameterSet.Config as cms

# DEFAULT
import os
datadir = os.path.join(os.environ.get('CMSSW_BASE',''),"src/HGCalCommissioning/LocalCalibration/data")

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
# input options (BIN -> RAW):
options.register('runNumber', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('maxEventsPerLumiSection', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Break in lumi sections using this event count")
options.register('fedId', [0], VarParsing.multiplicity.list, VarParsing.varType.int,
                 "FED IDs")
options.register('inputFiles',
                 '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/BeamTestAug/HgcalBeamtestAug2024/Relay1722382405/Run1722382405_Link1_File0000000001.bin',
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input DAQ link file")
options.register('inputTrigFiles', '',
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
###options.register('trigSeparator', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
###                 "Override default trigger packet separator (e.g. 0xcafecafe)")
# geometry options:
options.register('geometry', 'Extended2026D94', VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 'geometry to use')
options.register('modules',"HGCalCommissioning/Configuration/data/ModuleMaps/modulelocator_TB2024v1.txt",mytype=VarParsing.varType.string,
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
options.register('charMode', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Override characterization mode (-1: default from config YAML/JSON, 0: normal mode, 1: characterization mode)")
# module calibration & configurations:
options.register('fedconfig',f"{datadir}/config_feds_TB2024v1.json",mytype=VarParsing.varType.string,
                 info="Path to configuration (JSON format)")
options.register('modconfig',f"{datadir}/config_econds_TB2024v1.json",mytype=VarParsing.varType.string,
                 info="Path to configuration (JSON format)")
# verbosity options:
options.register('debug', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "debugging mode")
options.register('debugModules', '*', VarParsing.multiplicity.list, VarParsing.varType.string,
                 "debugging modules, default=['*']")
options.parseArguments()

# MAKE DEFAULTS
import re, glob
inputFiles = [ ] # cannot edit options.inputFiles
for fname in options.inputFiles:
  if '*' in fname: # expand glob wildcard and insert
    inputFiles.extend(glob.glob(fname))
  else:
    if not os.path.isfile(fname):
      print(f"WARNING! Input file file might not exist, or is not accessible? DAQ={fname}")
    inputFiles.append(fname)
if options.runNumber==-1:
  options.runNumber = 12345678 #1695762407
  if inputFiles: # extract run number from filename
    match = re.match(r".*Run(\d+)[^/]*\.bin$",inputFiles[0])
    if match:
      options.runNumber = int(match.group(1))
if options.inputTrigFiles==[ ]: # default: use same as input files
  trigexp = re.compile(r"(Run\d+)_Link(\d+)_(File\d+\.bin)$")
  for fname in inputFiles:
    trigfname = trigexp.sub(r"\1_Link0_\3",fname)
    options.inputTrigFiles.append(trigfname)
    if not os.path.isfile(trigfname):
      print(f"WARNING! Trigger file might not exist, or is not accessible? DAQ={fname}, trigger={trigfname}")

# DEFAULTS
print(f">>> Max events:    {options.maxEvents!r}")
print(f">>> Run number:    {options.runNumber!r}")
print(f">>> Input files:   {inputFiles!r}")
print(f">>> Trigger files: {options.inputTrigFiles!r}")
print(f">>> Output files:  {options.output!r}")
print(f">>> fedIds:        {options.fedId!r}")
print(f">>> Module map:    {options.modules!r}")
print(f">>> SiCell map:    {options.sicells!r}")
print(f">>> SipmCell map:  {options.sipmcells!r}")

# PROCESS
from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9 as Era_Phase2
process = cms.Process('RAW2DIGI',Era_Phase2)

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
  inputs=cms.untracked.vstring(*inputFiles),
  trig_inputs=cms.untracked.vstring(*options.inputTrigFiles),
  ###trig_num_blocks=6;
  ###trig_scintillator_block_id=5;
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
  bePassthroughMode=cms.int32(options.mismatchPassthrough), # override: ignore ECON-D packet mismatches
  cbHeaderMarker=cms.int32(options.cbHeaderMarker),         # override: capture block header marker
  slinkHeaderMarker=cms.int32(options.slinkHeaderMarker),   # override: S-link header marker
  econdHeaderMarker=cms.int32(options.econdHeaderMarker),   # override: ECON-D header marker
  charMode=cms.int32(options.charMode),                     # override: characterization mode
  indexSource=cms.ESInputTag('hgCalMappingESProducer','')
)

# RAW -> DIGI producer
# https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/EventFilter/HGCalRawToDigi/plugins/HGCalRawToDigi.cc
#print(">>> Prepare RAW -> DIGI...")
process.testHGCalRawToDigi = cms.EDProducer( # EDProducer to load configurations for unpacker
  'TestHGCalRawToDigi',
  src=cms.InputTag('rawDataCollector'),
  fedIds=cms.vuint32(*options.fedId),
)

# DEFINE PROCESSES: full RAW -> DIGI
print(">>> Prepare RAW -> DIGI process...")
process.p = cms.Path(
  process.testHGCalRawToDigi # RAW -> DIGI
)

print(">>> Run process...")