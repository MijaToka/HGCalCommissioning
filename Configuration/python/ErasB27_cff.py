import FWCore.ParameterSet.Config as cms

Eras_B27 = {
    'B27': {
        '1': {
            'fedId':[0],
            'modules':'HGCalCommissioning/Configuration/data/ModuleMaps/modulelocator_Sep2024TBv1.txt',
            'fedconfig':'/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/SepTB2024/Calibrations/SepTB2024/config/config_feds_v1.json',
            'modconfig':'/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/SepTB2024/Calibrations/SepTB2024/config/config_econds_v1.json',
            'modcalib':None,
            'trig_scintillator_block':-1,
            'trig_num_blocks':6
        },
    },
}

Calibs_B27 = {
    'B27': {
        1726941148 : {
            "modcalib": "/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/SepTB2024/Calibrations/SepTB2024/level0_calib_Relay1726941148.json",
        }
    }
}

def CustomCalibs_B27(run : int):
    """Specific customizations for relays: e.g. pedestal taken after the run - not chronogical"""

    custom_calibs= {
    }

    if not run in custom_calibs:
        return None, {}

    refrun=custom_calibs[run]
    return refrun, Calibs_B27[custom_calibs[refrun]]
