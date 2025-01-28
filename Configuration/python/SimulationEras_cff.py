import FWCore.ParameterSet.Config as cms
import re

def initSimulationCMSProcess(procname : str, maxEvents : int = -1, modulemapper : str = 'modulemapper.txt') -> cms.Process:
    """common declarations for simulation tests: geometry is dummy, it's just the latest"""

    #INIT PROCESS
    from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9 as Era_Phase2
    process = cms.Process(procname,Era_Phase2)

    #MAX EVENTS TO PROCESS
    process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(maxEvents) )

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

    #geometry and indexing
    import os
    geometry = "GeometryExtendedRun4D104" # for CMSSW >= 14.2
    geomfile = os.path.join(os.getenv('CMSSW_RELEASE_BASE',"nocmssw"),f"src/Configuration/Geometry/python/{geometry}Reco_cff.py")
    if not os.path.isfile(geomfile):
        print(f"Warning! Could not find {geometry} for CMSSW >= 14.2 in {geomfile}, using 2026 instead...")
        geometry = "GeometryExtended2026D104" # for CMSSW <= 14.1
    process.load(f"Configuration.Geometry.{geometry}Reco_cff")
    process.load(f"Configuration.Geometry.{geometry}_cff")
    from Geometry.HGCalMapping.hgcalmapping_cff import customise_hgcalmapper
    process = customise_hgcalmapper(process, modules=modulemapper)

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
    #sas file in path is used check if file is in eos and transform it with a relative path to CMSSW_BASE
    modcalib=eraConfig['modcalib']
    if modcalib.find('/eos/cms')==0:
        import os
        tkns = f'{os.environ["CMSSW_BASE"]}/src'.split('/')
        relpath = '/'.join( ['..']*len(tkns) )
        modcalib=relpath+modcalib
    process.hgcalCalibParamESProducer = cms.ESProducer( # ESProducer to load calibration parameters from JSON file, like pedestals
        'hgcalrechit::HGCalCalibrationESProducer@alpaka',
        filename=cms.FileInPath(modcalib),
        indexSource=cms.ESInputTag('hgCalMappingESProducer',''),
        configSource=cms.ESInputTag('hgcalConfigESProducer', '')
    )


    return process
