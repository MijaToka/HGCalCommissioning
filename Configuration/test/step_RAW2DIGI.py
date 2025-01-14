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
import glob
run = options.run
lumi = options.lumi
era = options.era
inputFiles = [ glob.glob(url) for url in options.files]
inputTrigFiles = [ glob.glob(url) for url in options.inputTrigFiles]
if len(inputFiles) != len(inputTrigFiles):
    raise ValueError('Number of input files does not match trigger files!!!')
if len(inputFiles)<0:
    raise ValueError('Missing input files')
print(f'Starting RAW2DIGI of Run={run} Lumi={lumi} with era={era}')
print(f'\t files={inputFiles}')
print(f'\t trigger files={inputTrigFiles}')
yamls = json.loads(options.yamls.replace("'", '"'))
print(f'\t yamls dict:')
rich.print(yamls)

from HGCalCommissioning.Configuration.SysValEras_cff import *
process, eraConfig = initSysValCMSProcess( procname='RAW2DIGI', era=era, run=run, maxEvents=options.maxEvents)

print(f'Era = {era} has the following config')
print(eraConfig)

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
    trig_num_blocks=cms.untracked.uint32(eraConfig['trig_num_blocks']),
    trig_scintillator_block_id=cms.untracked.int32(eraConfig['trig_scintillator_block'])
)
process.rawDataCollector = cms.EDAlias(
  source=cms.VPSet(
    cms.PSet(type=cms.string('FEDRawDataCollection'))
  )
)

process.trgRawDataCollector = cms.EDAlias(
  source=cms.VPSet(
    cms.PSet(type=cms.string('TrgFEDRawDataCollection'))
  )
)

# RAW -> DIGI producer
# process.load('HGCalCommissioning.HGCalRawToDigiTrigger.hgcalDigis_cfi')
# process.load('HGCalCommissioning.HGCalRawToDigiTrigger.HGCalRawToDigiTrigger_cfi')


process.hgcalDigis = cms.EDProducer(
  'HGCalRawToDigiTrigger'
)
process.hgcalDigis.src = cms.InputTag('rawDataCollector')
process.hgcalDigis.src_trigger = cms.InputTag('trgRawDataCollector')

# Select which unpacker specialization class to use for the unpacking:
process.hgcalDigis.unpacking_configuration = cms.string('TBsep24')

process.hgcalDigis.fedIds = cms.vuint32(*eraConfig['fedId'])

process.t = cms.Task(process.hgcalDigis)

process.p = cms.Path(
    process.t                    # RAW -> DIGI
    # process.hgcalDigis                    # RAW -> DIGI
)

process.output = cms.OutputModule(
  "PoolOutputModule",
  fileName=cms.untracked.string(options.output),
  outputCommands=cms.untracked.vstring(
    'drop *',
    'keep HGCalTestSystemMetaData_*_*_*',
    'keep TrgFEDRawDataCollection_*_*_*',
    'keep FEDRawDataCollection_*_*_*',
    'keep *SoA*_hgcalDigis_*_*',
  ),
  SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('p'))
)
process.outpath = cms.EndPath(process.output)
