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
options.register('runNumber', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('maxEventsPerLumiSection', -1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "Break in lumi sections using this event count")
options.register('firstEventToProcess', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "first event to process; will skip any events before this")
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
options.register('params',f"{datadir}/level0_calib_params_TB2024v1.json",mytype=VarParsing.varType.string,
                 info="Path to calibration parameters (JSON format)")
options.register('gpu', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run on GPUs")
# nano options:
options.register('skipDigi', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "skip Digis for flat NANO table")
# DQM options (DIGI -> DQM):
options.register('prescale', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "prescale for DQM (to reduce amount of output data)")
options.register('dqmOnly', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "run only the DQM step")
# output options:
options.register('dumpFRD', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also dump the FEDRawData content")
options.register('storeOutput', True, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also store the output into an EDM file")
options.register('storeNANOOutput', True, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also store the flat NANOAOD file")
options.register('storeRAWOutput', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also store the RAW output into a streamer file")
# verbosity options:
options.register('debug', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "debugging mode")
options.register('debugModules', '*', VarParsing.multiplicity.list, VarParsing.varType.string,
                 "debugging modules, default=['*']")
options.parseArguments()

# MAKE DEFAULTS
import re, glob
inputFiles = [ ] # cannot edit options.inputFiles
outputFile = options.output # cannot edit options.output
for fname in options.inputFiles:
  if any(c in fname for c in '[*?'): # expand glob wildcard and insert
    matches = glob.glob(fname)
    if not matches:
      print(f"WARNING! Found no input files for glob pattern {fname!r}...")
    inputFiles.extend(matches)
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
  trigexp = re.compile(r"(Run\d+)_Link(\d+)_(File\d+\.bin)$") # look for _LinkX_
  for fname in inputFiles:
    trigfname = trigexp.sub(r"\1_Link0_\3",fname) # replace _LinkX_ -> _Link0_
    options.inputTrigFiles.append(trigfname)
    if not os.path.isfile(trigfname):
      print(f"WARNING! Trigger file might not exist, or is not accessible? DAQ={fname}, trigger={trigfname}")
outputFile = outputFile.replace("_RunRUN",f"_Run{options.runNumber:010d}") # fill placeholder
nanoOutputFile = os.path.join(os.path.dirname(outputFile),f"nano_{os.path.basename(outputFile)}")
doNANO = options.storeNANOOutput and not (options.skipDigi and options.dqmOnly)
if os.path.isfile(outputFile):
  print(f"WARNING! Output file already exists! You may need to remove it to prevent 'Fatal Root Error: @SUB=TStorageFactorySystem::Unlink'")

# DEFAULTS
print(f">>> Max events:    {options.maxEvents!r}")
print(f">>> Run number:    {options.runNumber!r}")
print(f">>> Input files:   {inputFiles!r}")
print(f">>> Trigger files: {options.inputTrigFiles!r}")
print(f">>> Output file:   {outputFile!r}")
print(f">>> NANO file:     {nanoOutputFile!r}")
print(f">>> fedIds:        {options.fedId!r}")
print(f">>> Module map:    {options.modules!r}")
print(f">>> SiCell map:    {options.sicells!r}")
print(f">>> SipmCell map:  {options.sipmcells!r}")
print(f">>> Calib params:  {options.params!r}")
#print(f">>> dqmOnly={options.dqmOnly!r}, skipDigi={options.skipDigi!r}, doNANO={doNANO!r}")

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
  'HGCalSlinkFromRawSource',
  isRealData=cms.untracked.bool(True),
  runNumber=cms.untracked.uint32(options.runNumber),
  firstLumiSection=cms.untracked.uint32(1),
  maxEventsPerLumiSection=cms.untracked.int32(options.maxEventsPerLumiSection),
  useL1EventID=cms.untracked.bool(True),
  fedIds=cms.untracked.vuint32(*options.fedId),
  inputs=cms.untracked.vstring(*inputFiles),
  trig_inputs=cms.untracked.vstring(*options.inputTrigFiles),
  firstRun=cms.untracked.uint32(options.runNumber),
  firstEvent=cms.untracked.uint32(options.firstEventToProcess),
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
# https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/HGCalConfigurationESProducer.cc
process.hgcalConfigESProducer = cms.ESSource( # ESProducer to load configurations for unpacker
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

# CALIBRATIONS & CONFIGURATION Alpaka ESProducers (for DIGI -> RECO step)
# https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitConfigurationESProducer.cc
# https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitCalibrationESProducer.cc
if not options.dqmOnly:
  #print(">>> Prepare calibrations & configuration...")
  #process.load('HeterogeneousCore.AlpakaCore.ProcessAcceleratorAlpaka_cfi')
  #process.load('HeterogeneousCore.CUDACore.ProcessAcceleratorCUDA_cfi')
  process.hgcalConfigParamESProducer = cms.ESProducer( # ESProducer to load configurations parameters from YAML file, like gain
    'hgcalrechit::HGCalConfigurationESProducer@alpaka',
    gain=cms.int32(1), # override to switch between 80, 160, 320 fC calibration
    #charMode=cms.int32(options.charMode),
    indexSource=cms.ESInputTag('hgCalMappingESProducer',''),
  )
  process.hgcalCalibParamESProducer = cms.ESProducer( # ESProducer to load calibration parameters from JSON file, like pedestals
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

# DIGI -> DQM
# https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/DQM/plugins/HGCalSysValDigisClient.cc
# https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/DQM/plugins/HGCalSysValDigisHarvester.cc
if options.dqmOnly:
  process.load('HGCalCommissioning.DQM.hgCalSysValDigisClient_cfi')
  process.load('HGCalCommissioning.DQM.hgCalSysValDigisHarvester_cfi')
  process.load("DQMServices.FileIO.DQMFileSaverOnline_cfi")
  process.hgCalSysValDigisClient.PrescaleFactor = options.prescale
  #process.hgCalSysValDigisClient.MetaData = cms.InputTag('rawMetaDataCollector'),
  process.DQMStore = cms.Service("DQMStore")
  process.dqmSaver.tag = 'HGCAL'
  process.dqmSaver.runNumber = options.runNumber

# DIGI -> RECO producer
# https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/RecoLocalCalo/HGCalRecAlgos/plugins/alpaka/HGCalRecHitsProducer.cc
else:
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
# https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/NanoTools/plugins/HGCalNanoTableProducer.cc
# https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/NanoTools/plugins/HGCalRunFEDReadoutSequence.cc
if doNANO:
  #print(">>> Prepare DIGI/RECO -> NANO...")
  process.load('HGCalCommissioning.NanoTools.hgCalNanoTableProducer_cfi')
  process.load('HGCalCommissioning.NanoTools.hgCalRunFEDReadoutSequence_cfi')
  process.hgcalNanoFlatTable = cms.EDProducer(
    'HGCalNanoTableProducer',
    metadata=cms.InputTag('rawMetaDataCollector', ''), #, 'LHC'),
    digis=cms.InputTag('hgcalDigis', '', 'RAW2RECO'),
    rechits=cms.InputTag('hgcalRecHits', '', 'RAW2RECO'),
    skipDigi=cms.bool(options.skipDigi),
    skipRecHits=cms.bool(options.dqmOnly) # skip DIGI -> RECO for DQM only
  )
  process.hgcalNanoRunFlatTable = cms.EDProducer(
    'HGCalRunFEDReadoutSequence', # Run tables
  )

# DEFINE PROCESSES:
if options.dqmOnly: # RAW -> DIGI -> DQM only
  print(">>> Prepare RAW -> DIGI -> DQM process...")
  process.p = cms.Path(
    #*process.hgCalEmptyEventFilter    # FILTER empty events
    process.hgcalDigis                 # RAW -> DIGI
    *process.hgCalSysValDigisClient    # DIGI -> DQM
    *process.hgCalSysValDigisHarvester # harvest all histograms
    *process.dqmSaver                  # store to DQM_V*_HGCAL_R$RUNNUMBER.root file
  )
else: # RAW -> DIGI -> RECO
  print(">>> Prepare RAW -> DIGI -> RECO process...")
  process.p = cms.Path(
    #*process.hgCalEmptyEventFilter # FILTER empty events
    process.hgcalDigis              # RAW -> DIGI
    *process.hgcalRecHits           # DIGI -> RECO (RecHit calibrations)
  )
if doNANO: # DIGI/RECO -> NANO
  process.p *= process.hgcalNanoFlatTable # DIGI -> NANO (flat table)
  process.p *= process.hgcalNanoRunFlatTable # run SoA -> NANO (flat run table)

# DUMP FED
if options.dumpFRD:
  process.dump = cms.EDAnalyzer(
    'DumpFEDRawDataProduct',
    label=cms.untracked.InputTag('rawDataCollector'),
    feds=cms.untracked.vint32(*options.fedId),
    dumpPayload=cms.untracked.bool(True)
  )
  process.p *= process.dump

# OUTPUT
process.outpath = cms.EndPath()
if options.storeOutput:
  process.output = cms.OutputModule(
    'PoolOutputModule',
    fileName=cms.untracked.string(outputFile),
    outputCommands=cms.untracked.vstring(
      "drop *",
      "keep HGCalTestSystemMetaData_*_*_*",
      "keep FEDRawDataCollection_*_*_*",
      "keep *SoA*_hgcalDigis_*_*",
      "keep *SoA*_hgcalRecHits_*_*",
    ),
    #SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('p'))
  )
  process.outpath += process.output

# NANOAOD OUTPUT
if doNANO:
  process.NANOAODoutput = cms.OutputModule(
    'NanoAODOutputModule',
    compressionAlgorithm=cms.untracked.string('LZMA'),
    compressionLevel=cms.untracked.int32(9),
    dataset=cms.untracked.PSet(
      dataTier=cms.untracked.string('NANOAOD'),
      filterName=cms.untracked.string('')
    ),
    fileName=cms.untracked.string(nanoOutputFile),
    outputCommands=cms.untracked.vstring(
      "drop *",
      "keep nanoaodFlatTable_*Table_*_*",
    )
  )
  process.outpath += process.NANOAODoutput

# RAW OUTPUT
if options.storeRAWOutput:
  process.outputRAW = cms.OutputModule(
    'FRDOutputModule',
    fileName=cms.untracked.string(outputFile),
    source=cms.InputTag('rawDataCollector'),
    frdVersion=cms.untracked.uint32(6),
    frdFileVersion=cms.untracked.uint32(1),
  )
  process.outpath += process.outputRAW

print(">>> Run process...")
