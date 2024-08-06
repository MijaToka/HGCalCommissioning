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
options.register('inputTrigFiles',[],
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
options.register('yamls',None,
                 VarParsing.multiplicity.singleton, VarParsing.varType.string, "input Trigger link file")
options.parseArguments()

# get the options
import json
import rich
run = options.run
lumi = options.lumi
era = options.era
inputFiles = options.files
inputTrigFiles = options.inputTrigFiles
print(f'Starting RAW2DIGI of Run={run} Lumi={lumi} with era={era}')
print(f'\t files={inputFiles}')
print(f'\t trigger files={inputTrigFiles}')
yamls = json.loads(options.yamls.replace("'", '"'))
print(f'\t yamls dict:')
rich.print(yamls)

from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RAW2DIGI', era=era, maxEvents=options.maxEvents)
    
# INPUT
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.source = cms.Source(
  "HGCalSlinkFromRawSource",
  isRealData=cms.untracked.bool(True),
  runNumber=cms.untracked.uint32(run),
  firstLumiSection=cms.untracked.uint32(lumi),
  maxEventsPerLumiSection=cms.untracked.int32(-1),
  useL1EventID=cms.untracked.bool(True),
  fedIds=cms.untracked.vuint32(*eraConfig['fedId']),
  inputs=cms.untracked.vstring(*inputFiles),
  trig_inputs=cms.untracked.vstring(*inputTrigFiles),
)
process.rawDataCollector = cms.EDAlias(
  source=cms.VPSet(
    cms.PSet(type=cms.string('FEDRawDataCollection'))
  )
)

# GLOBAL HGCAL CONFIGURATION (for unpacker)
process.hgcalConfigESProducer = cms.ESSource( # ESProducer to load configurations for unpacker
  'HGCalConfigurationESProducer',
  fedjson=cms.string(eraConfig['fedconfig']), # JSON with FED configuration parameters
  modjson=cms.string(eraConfig['modconfig']), # JSON with ECON-D configuration parameters
  bePassthroughMode=cms.int32(-1),
  cbHeaderMarker=cms.int32(-1),
  slinkHeaderMarker=cms.int32(-1),
  econdHeaderMarker=cms.int32(-1),
  econPassthroughMode=cms.int32(-1),
  charMode=cms.int32(-1),
  gain=cms.int32(1),
  indexSource=cms.ESInputTag('hgCalMappingESProducer','')
)

# CALIBRATIONS & CONFIGURATION Alpaka ESProducers (for DIGI -> RECO step)
process.hgcalConfigParamESProducer = cms.ESProducer( # ESProducer to load configurations parameters from YAML file, like gain
  'hgcalrechit::HGCalConfigurationESProducer@alpaka',
  gain=cms.int32(1), # to switch between 80, 160, 320 fC calibration : Discuss with Izaak this line
  indexSource=cms.ESInputTag('hgCalMappingESProducer',''),
)
process.hgcalCalibParamESProducer = cms.ESProducer( # ESProducer to load calibration parameters from JSON file, like pedestals
  'hgcalrechit::HGCalCalibrationESProducer@alpaka',
  filename=cms.string(eraConfig['modcalib']),
  indexSource=cms.ESInputTag('hgCalMappingESProducer',''),
  configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
)

# RAW -> DIGI producer
process.load('EventFilter.HGCalRawToDigi.hgcalDigis_cfi')
process.hgcalDigis.src = cms.InputTag('rawDataCollector')
process.hgcalDigis.fedIds = cms.vuint32(*eraConfig['fedId'])

process.p = cms.Path(
    process.hgcalDigis                    # RAW -> DIGI
)

process.output = cms.OutputModule(
  "PoolOutputModule",
  fileName=cms.untracked.string(options.output),
  outputCommands=cms.untracked.vstring(
    'drop *',
    'keep HGCalTestSystemMetaData_*_*_*',
    'keep FEDRawDataCollection_*_*_*',
    'keep *SoA*_hgcalDigis_*_*',
  ),
  SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('p'))
)
process.outpath = cms.EndPath(process.output)
