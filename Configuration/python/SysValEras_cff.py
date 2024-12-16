import FWCore.ParameterSet.Config as cms
import re

from HGCalCommissioning.Configuration.ErasSepTB2024_cff import Eras_SepTB2024, Calibs_SepTB2024, CustomCalibs_SepTB2024

_SysValEras = {}
_SysValEras.update(Eras_SepTB2024)

_SysValCalibs = {}
_SysValCalibs.update(Calibs_SepTB2024)


def findAppropriateCalib(run : int, calib_dict : dict) -> dict:
    """checks which is the closest preceding relay / run for which a calibration is available, if none return the default one"""

    #sort by increasing run number: stop first negative difference (=>run < ref_run)
    available_refs = sorted([r for r in calib_dict.keys() if type(r)==int], reverse=False)
    refrun = available_refs[0]
    for i in range(1,len(available_refs)):
        delta = run - available_refs[i]
        if delta<0 : break
        refrun = available_refs[i]

    #print(f'Will use as reference run{run}')
          
    #return calib from reference run
    return refrun, calib_dict[refrun]


def getEraConfiguration(era : str, run : int) -> dict :
    """gets the appropriate configuration to use from the eras dict
    run is used to fine tune the calibration and configurations used
    """
    
    groups=re.findall('(.*)/v(\\d+)',era)
    if len(groups)!=1 or len(groups[0])!=2 :
        raise ValueError(f'Could not decode era {era}')

    setup,version = groups[0]
    if not setup in _SysValEras:
        raise ValueError(f'Setup {setup} is not found in configuration')
    if not version in _SysValEras[setup]:
        raise ValueError(f'Version {version} of setup {setup} is not found in configuration')
    if not setup in _SysValCalibs:
        raise ValueError(f'Setup {setup} is not found in calibrations')

    refrun, calib = globals()[f'CustomCalibs_{setup}'](run)
    if refrun is None:
        print('No pre-defined reference run: falling back on timestamp based references') 
        refrun, calib = findAppropriateCalib(run=run, calib_dict=_SysValCalibs[setup])
    print(f'Reference run is {refrun}')
    
    cfg = _SysValEras[setup][version].copy()
    cfg.update(calib)
    cfg['ReferenceRun'] = refrun
    
    return cfg


def initSysValCMSProcess(procname : str, era : str, run : int, maxEvents : int = -1) -> (cms.Process, dict):
    """common declarations for sysval tests: geometry is dummy, it's just the latest"""

    eraConfig = getEraConfiguration(era=era, run=run)

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
    process = customise_hgcalmapper(process, modules=eraConfig['modules'])

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
    
    # TIMING Report
    process.Timing = cms.Service("Timing",
                                 summaryOnly=cms.untracked.bool(True),
                                 useJobReport=cms.untracked.bool(True))


    return (process, eraConfig)


if __name__ == '__main__':

    #SepTB2024 hardware-driven eras
    hweras = [1726178015, 1726313281, 1727030266]

    #SepTB2024 selected relays
    relays = [1726225188, 1726304466, 1726346360, 1726428151, 1726512750, 1726589326, 1726763542, 1726909688, 1726920438, 1726941148, 1727033054, 1727101030, 1727116899, 1727124229, 1727132348, 1727169610, 1727170256, 1727173910, 1727180386, 1727185107, 1727203674, 1727206089, 1727207396, 1727208074, 1727208484, 1727208963, 1727209457, 1727209838, 1727210224, 1727210663, 1727211076, 1727217678]

    relay_table=[]
    for r in relays:

        ref_idx = -1
        for idx, rr in enumerate(hweras[::-1]) :
            if r-rr<0 : continue
            ref_idx = len(hweras)-1-idx
            break
        era = f'SepTB2024/v{ref_idx+1}' if ref_idx>=0 else 'Default'
        era_config = getEraConfiguration(era,r)
        relay_table.append( f'| {r:5d} | {era} | {era_config["ReferenceRun"]} |')
    print('\n'.join(relay_table))
