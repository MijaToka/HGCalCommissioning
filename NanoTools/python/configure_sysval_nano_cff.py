import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

def setArgParserForNANO(options : VarParsing, skipRecHitsDefault : bool = False):
    """sets the options needed to parse commandline arguments for the RAW2DIGI step"""
    if not options.has_key('era'):
        options.register('era', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                         "reconstruction era")
    if not options.has_key('run'):
        options.register('run', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                         "run number")
    options.register('skipRecHits', skipRecHitsDefault, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                     "skip RecHits table")
    options.register('skipMeta', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                     "skip metadata table")
    options.register('skipECON', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                     "skip ECON table")
    options.register('isSimulation', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                     "adapt for simulated samples")
    options.register('modmap', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                     "use instead this module mapper file")
    return options
    
def configureNANOStep(process, options, maxThreads : int = 4):
    
    """adds the needed configuration for the NANO output"""

    
    # OPTIONS
    process.options = cms.untracked.PSet(
        IgnoreCompletely = cms.untracked.vstring(),
        Rethrow = cms.untracked.vstring(),
        TryToContinue = cms.untracked.vstring(),
        accelerators = cms.untracked.vstring('*'),
        allowUnscheduled = cms.obsolete.untracked.bool,
        canDeleteEarly = cms.untracked.vstring(),
        deleteNonConsumedUnscheduledModules = cms.untracked.bool(True),
        dumpOptions = cms.untracked.bool(False),
        emptyRunLumiMode = cms.obsolete.untracked.string,
        eventSetup = cms.untracked.PSet(
            forceNumberOfConcurrentIOVs = cms.untracked.PSet(
                allowAnyLabel_=cms.required.untracked.uint32
            ),
            numberOfConcurrentIOVs = cms.untracked.uint32(0)
        ),
        fileMode = cms.untracked.string('FULLMERGE'),
        forceEventSetupCacheClearOnNewRun = cms.untracked.bool(False),
        holdsReferencesToDeleteEarly = cms.untracked.VPSet(),
        makeTriggerResults = cms.obsolete.untracked.bool,
        modulesToCallForTryToContinue = cms.untracked.vstring(),
        modulesToIgnoreForDeleteEarly = cms.untracked.vstring(),
        numberOfConcurrentLuminosityBlocks = cms.untracked.uint32(0),
        numberOfConcurrentRuns = cms.untracked.uint32(1),
        numberOfStreams = cms.untracked.uint32(0),
        numberOfThreads = cms.untracked.uint32(maxThreads),
        printDependencies = cms.untracked.bool(False),
        sizeOfStackForThreadsInKB = cms.optional.untracked.uint32,
        throwIfIllegalParameter = cms.untracked.bool(True),
        wantSummary = cms.untracked.bool(False)
    )

    # Production Info
    process.configurationMetadata = cms.untracked.PSet(
        annotation = cms.untracked.string('NANO nevts:-1'),
        name = cms.untracked.string('Applications'),
        version = cms.untracked.string('$Revision: 1.19 $')
    )

    # Output definition
    process.NANOAODoutput = cms.OutputModule("NanoAODOutputModule",
                                             compressionAlgorithm = cms.untracked.string('ZSTD'),
                                             compressionLevel = cms.untracked.int32(5),
                                             dataset = cms.untracked.PSet(
                                                 dataTier = cms.untracked.string('NANOAOD'),
                                                 filterName = cms.untracked.string('')
                                             ),
                                             fileName = cms.untracked.string('NANO.root'),
                                             outputCommands = process.NANOAODEventContent.outputCommands
                                             )
    
    # Additional output definition
    process.load('HGCalCommissioning.NanoTools.hgcSysValNano_cff')
    process.hgCalNanoTable.skipRecHits = cms.bool(options.skipRecHits)
    process.hgCalNanoTable.skipMeta = cms.bool(options.skipMeta)
    process.hgCalNanoTable.skipECON = cms.bool(options.skipECON)
    process.nano_path = cms.Path(process.hgcSysValNanoTask)

    # end steps and Schedule definition
    process.load('SimGeneral.HepPDTESSource.pythiapdt_cfi')
    process.load('Configuration.EventContent.EventContent_cff')
    process.load('Configuration.StandardSequences.EndOfProcess_cff')    
    process.endjob_step = cms.EndPath(process.endOfProcess)
    process.NANOAODoutput_step = cms.EndPath(process.NANOAODoutput)
    process.maxEvents.output = cms.optional.untracked.allowed(cms.int32,cms.PSet)
    process.schedule = cms.Schedule(process.nano_path,process.endjob_step,process.NANOAODoutput_step)

    #add pat algos tools task (probably not needed for SysVal...)
    from PhysicsTools.PatAlgos.tools.helpers import associatePatAlgosToolsTask
    associatePatAlgosToolsTask(process)

    # Add early deletion of temporary data products to reduce peak memory need
    from Configuration.StandardSequences.earlyDeleteSettings_cff import customiseEarlyDelete
    process = customiseEarlyDelete(process)

    return process
