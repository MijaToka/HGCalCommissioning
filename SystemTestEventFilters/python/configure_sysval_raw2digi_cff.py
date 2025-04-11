import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
import json
import rich
import glob

def setArgParserForRAW2DIGI(options : VarParsing):
    """sets the options needed to parse commandline arguments for the RAW2DIGI step"""
    
    options.register('run', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                     "run number")
    options.register('lumi', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                     "first lumi section")
    options.register('era', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                     "reconstruction era")
    options.register('inputTrigFiles',[],
                     VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
    options.register('enableTPGunpacker', False,
                     VarParsing.multiplicity.singleton, VarParsing.varType.bool, "unpack also TPGs")
    options.register('yamls',None,
                     VarParsing.multiplicity.singleton, VarParsing.varType.string, "input Trigger link file")
    return options

def configureRAW2DIGIStep(process, options, eraConfig : dict):
    
    # get the options
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
    
    #start the RAW2DIGI producer
    if options.enableTPGunpacker:
        process.trgRawDataCollector = cms.EDAlias(
            source=cms.VPSet(
                cms.PSet(type=cms.string('TrgFEDRawDataCollection'))
            )
        )
        
        process.hgcalDigis = cms.EDProducer('HGCalRawToDigiTrigger')
        process.hgcalDigis.src_trigger = cms.InputTag('trgRawDataCollector')
        
    else:
        process.hgcalDigis = cms.EDProducer('HGCalRawToDigi')

        
        #final configuration of digi producer
        process.hgcalDigis.src = cms.InputTag('rawDataCollector')
        process.hgcalDigis.fedIds = cms.vuint32(*eraConfig['fedId'])
    
    process.raw2digi_step = cms.Path(process.hgcalDigis)

    return process

    
