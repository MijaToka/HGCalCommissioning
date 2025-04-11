import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

def setArgParserForRECO(options : VarParsing):
    """sets the options needed to parse commandline arguments for the RAW2DIGI step"""
    if not options.has_key('era'):
        options.register('era', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                         "reconstruction era")
    if not options.has_key('run'):
        options.register('run', None, VarParsing.multiplicity.singleton, VarParsing.varType.int,
                         "run number")
    options.register('gpu', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool,
                     "run on GPUs")
    options.register('calibfile', None, VarParsing.multiplicity.singleton, VarParsing.varType.string,
                     "use this calibration file instead of the era-based one")
    return options
    
def configureRECOStep(process, options):
    
    """adds the needed configuration for the RECO step"""
    #DIGI -> RECO
    process.load('HeterogeneousCore.AlpakaCore.ProcessAcceleratorAlpaka_cfi')
    process.load('HeterogeneousCore.CUDACore.ProcessAcceleratorCUDA_cfi')
    if options.gpu:
        process.hgcalRecHits = cms.EDProducer(
            'alpaka_cuda_async::HGCalRecHitsProducer',
            digis=cms.InputTag('hgcalDigis', ''),
            calibSource=cms.ESInputTag('hgcalCalibParamESProducer', ''),
            configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
            n_hits_scale=cms.int32(1),
            n_blocks=cms.int32(4096),
            n_threads=cms.int32(1024)
        )
    else:
        process.hgcalRecHits = cms.EDProducer(
            'alpaka_serial_sync::HGCalRecHitsProducer',
            digis=cms.InputTag('hgcalDigis', ''),
            calibSource=cms.ESInputTag('hgcalCalibParamESProducer', ''),
            configSource=cms.ESInputTag('hgcalConfigParamESProducer', ''),
            n_hits_scale=cms.int32(1),
            n_blocks=cms.int32(1024),
            n_threads=cms.int32(4096)
        )
    
    process.reco_task = cms.Task( process.hgcalRecHits )
    
    return process
