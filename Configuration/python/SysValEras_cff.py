import FWCore.ParameterSet.Config as cms
import re

_sysvalconfig = {
    'B27': {
        '1': {
            'fedId':[0],
            'modules':'HGCalCommissioning/Configuration/data/ModuleMaps/modulelocator_B27v1.txt',
            'fedconfig':'HGCalCommissioning/LocalCalibration/data/config_feds_B27v1.json',
            'modconfig':'HGCalCommissioning/LocalCalibration/data/config_econds_B27v1.json',
            'modcalib':'HGCalCommissioning/LocalCalibration/data/level0_calib_params_B27v1.json'
        },
    },
    'TB2024': {
        '1': {
            'fedId':[0],
            'modules':'HGCalCommissioning/Configuration/data/ModuleMaps/modulelocator_TB2024v1.txt',
            'fedconfig':'HGCalCommissioning/LocalCalibration/data/config_feds_TB2024v1.json',
            'modconfig':'HGCalCommissioning/LocalCalibration/data/config_econds_TB2024v1.json',
            'modcalib':'HGCalCommissioning/LocalCalibration/data/level0_calib_params_B27v1.json'
        },
    },
}

def getEraConfiguration(era : str) -> dict :
    """gets the appropriate configuration to use from the eras dict"""
    
    groups=re.findall('(.*)/v(\\d+)',era)
    if len(groups)!=1 or len(groups[0])!=2 :
        raise ValueError(f'Could not decode era {era}')

    setup,version = groups[0]
    if not setup in _sysvalconfig:
        raise ValueError(f'Setup {setup} is not found in configuration')
    if not version in _sysvalconfig[setup]:
        raise ValueError(f'Version {version} of setup {setup} is not found in configuration')
    
    return _sysvalconfig[setup][version]


def initSysValCMSProcess(procname : str, era : str, maxEvents : int = -1) -> (cms.Process, dict):
    """common declarations for sysval tests: geometry is dummy, it's just the latest"""

    eraConfig = getEraConfiguration(era=era)

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
    process.load(f"Configuration.Geometry.GeometryExtended2026D104Reco_cff")
    process.load(f"Configuration.Geometry.GeometryExtended2026D104_cff")
    from Geometry.HGCalMapping.hgcalmapping_cff import customise_hgcalmapper
    process = customise_hgcalmapper(process, modules=eraConfig['modules'])

    # TIMING Report
    process.Timing = cms.Service("Timing",
                                 summaryOnly=cms.untracked.bool(True),
                                 useJobReport=cms.untracked.bool(True))


    return (process, eraConfig)