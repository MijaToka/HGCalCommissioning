import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

process = cms.Process("TEST")

options = VarParsing('standard')
# inputs
options.register(
    'runNumber', 1, VarParsing.multiplicity.singleton, VarParsing.varType.int, "run number")
options.register(
    'fedId', [0], VarParsing.multiplicity.list, VarParsing.varType.int, "FED IDs")
options.register(
    'inputFiles',
    '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link1_File0000000001.bin',
    VarParsing.multiplicity.list, VarParsing.varType.string, "input DAQ link file")
options.register(
    'inputTrigFiles',
    '/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/BeamTestSep/HgcalBeamtestSep2023/Relay1695762407/Run1695762407_Link0_File0000000001.bin',
    VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
# configs
options.register(
    'modules', 'Geometry/HGCalMapping/data/ModuleMaps/modulelocator_test.txt', mytype=VarParsing.varType.string,
    info="Path to module mapper. Absolute, or relative to CMSSW src directory")
options.register(
    'sicells', 'Geometry/HGCalMapping/data/CellMaps/WaferCellMapTraces.txt', mytype=VarParsing.varType.string,
    info="Path to Si cell mapper. Absolute, or relative to CMSSW src directory")
options.register(
    'sipmcells', 'Geometry/HGCalMapping/data/CellMaps/channels_sipmontile.hgcal.txt', mytype=VarParsing.varType.string,
    info="Path to SiPM-on-tile cell mapper. Absolute, or relative to CMSSW src directory")
# options
options.register(
    'dumpFRD', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
    "also dump the FEDRawData content")
options.register(
    'storeRAWOutput', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
    "also store the RAW output into a streamer file")
options.register(
    'storeOutput', True, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
    "also store the output into an EDM file")
options.register(
    'debug', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
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

# source
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
process.rawDataCollector = cms.EDAlias(
    source=cms.VPSet(
        cms.PSet(type=cms.string('FEDRawDataCollection'))
    )
)

# logical mapping
process.load('Geometry.HGCalMapping.hgCalMappingIndexESSource_cfi')
process.hgCalMappingIndexESSource.modules = cms.FileInPath(options.modules)
process.hgCalMappingIndexESSource.si = cms.FileInPath(options.sicells)
process.hgCalMappingIndexESSource.sipm = cms.FileInPath(options.sipmcells)

process.load('Configuration.StandardSequences.Accelerators_cff')
process.hgCalMappingModuleESProducer = cms.ESProducer('hgcal::HGCalMappingModuleESProducer@alpaka',
                                                      filename=cms.FileInPath(options.modules),
                                                      moduleindexer=cms.ESInputTag(''))
process.hgCalMappingCellESProducer = cms.ESProducer('hgcal::HGCalMappingCellESProducer@alpaka',
                                                    filelist=cms.vstring(options.sicells, options.sipmcells),
                                                    cellindexer=cms.ESInputTag(''))


process.load('EventFilter.HGCalRawToDigi.hgcalDigis_cfi')
process.hgcalDigis.src = cms.InputTag('rawDataCollector')
process.hgcalDigis.fedIds = cms.vuint32(*options.fedId)

# process.hgcalDigis.maxCaptureBlock = process.hgcalEmulatedSlinkRawData.slinkParams.numCaptureBlocks
# process.hgcalDigis.numERxsInECOND = options.numERxsPerECOND
# process.hgcalDigis.captureBlockECONDMax = max(  # allows to mess with unconventional, high number of ECON-Ds per capture block
#     process.hgcalDigis.captureBlockECONDMax,
#     len([ec for ec in process.hgcalEmulatedSlinkRawData.slinkParams.ECONDs if ec.active]))

# process.hgcalDigis.configSource = cms.ESInputTag('')  # for HGCalConfigESSourceFromYAML
# process.hgcalDigis.moduleInfoSource = cms.ESInputTag('')  # for HGCalModuleInfoESSource
# process.hgcalDigis.slinkBOE = cms.uint32(options.slinkBOE)
# process.hgcalDigis.cbHeaderMarker = cms.uint32(options.cbHeaderMarker)
# process.hgcalDigis.econdHeaderMarker = cms.uint32(options.econdHeaderMarker)
# process.hgcalDigis.applyFWworkaround = options.applyFWworkaround
# process.hgcalDigis.swap32bendianness = options.swap32bendianness

process.p = cms.Path(process.hgcalDigis)

process.outpath = cms.EndPath()

if options.storeOutput:
    process.output = cms.OutputModule("PoolOutputModule",
                                      fileName=cms.untracked.string(options.output),
                                      outputCommands=cms.untracked.vstring(
                                          'drop *',
                                          #   'keep *_hgcalEmulatedSlinkRawData_*_*',
                                          'keep *_hgcalDigis_*_*',
                                          #   'keep *_hgcalRecHit_*_*',
                                          #   'keep *_hgCalRecHitsFromSoAproducer_*_*',
                                      ),
                                      #   SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring('p'))
                                      )
    process.outpath += process.output

if options.dumpFRD:
    process.dump = cms.EDAnalyzer("DumpFEDRawDataProduct",
                                  label=cms.untracked.InputTag('rawDataCollector'),
                                  feds=cms.untracked.vint32(*options.fedId),
                                  dumpPayload=cms.untracked.bool(True)
                                  )
    process.p *= process.dump

if options.storeRAWOutput:
    process.outputRAW = cms.OutputModule("FRDOutputModule",
                                         fileName=cms.untracked.string(options.output),
                                         source=cms.InputTag('rawDataCollector'),
                                         frdVersion=cms.untracked.uint32(6),
                                         frdFileVersion=cms.untracked.uint32(1),
                                         )
    process.outpath += process.outputRAW
