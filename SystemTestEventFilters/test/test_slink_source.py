import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

process = cms.Process("TEST")

options = VarParsing('standard')
options.register('runNumber', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                 "run number")
options.register('fedId', [0], VarParsing.multiplicity.list, VarParsing.varType.int,
                 "FED IDs")
options.register(
    'inputFiles',
    '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link1_File0000000001.bin',
    VarParsing.multiplicity.list, VarParsing.varType.string, "input DAQ link file")
options.register(
    'inputTrigFiles',
    '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link0_File0000000001.bin',
    VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
options.register('dumpFRD', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also dump the FEDRawData content")
options.register('storeRAWOutput', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "also store the RAW output into a streamer file")
options.register('debug', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                 "debugging mode")
options.parseArguments()

# message logger
process.load("FWCore.MessageService.MessageLogger_cfi")
process.MessageLogger.cerr.FwkReport.reportEvery = 50000
if options.debug:
    process.MessageLogger.cerr.threshold = 'DEBUG'
    process.MessageLogger.debugModules = options.debugModules  # default: ['*']
    process.MessageLogger.cerr.DEBUG = cms.untracked.PSet(
        limit=cms.untracked.int32(-1)
    )
process.options.wantSummary = cms.untracked.bool(True)

# source is empty source
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

process.p = cms.Path()

process.outpath = cms.EndPath()

if options.dumpFRD:
    process.dump = cms.EDAnalyzer("DumpFEDRawDataProduct",
                                  label=cms.untracked.InputTag('source'),
                                  feds=cms.untracked.vint32(*options.fedId),
                                  dumpPayload=cms.untracked.bool(True)
                                  )
    process.p *= process.dump

if options.storeRAWOutput:
    process.outputRAW = cms.OutputModule("FRDOutputModule",
                                         fileName=cms.untracked.string(options.output),
                                         source=cms.InputTag('source'),
                                         frdVersion=cms.untracked.uint32(6),
                                         frdFileVersion=cms.untracked.uint32(1),
                                         )
    process.outpath += process.outputRAW
