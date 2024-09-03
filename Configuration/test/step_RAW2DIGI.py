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
