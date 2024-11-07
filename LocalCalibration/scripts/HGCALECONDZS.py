import sys
import argparse
import json
import numpy as np

from PrepareLevel0CalibParams import buildLevel0CalibParams

def fillECONDconfig(path_to_config : str, CE : float, mip_sf : float, mip_sf_m1 : float, cmtype : str, onlyPedestals : bool = False, P_CM_correction : bool = False, P_CM_BXm1_correction : bool = False , factor : int = 1) -> dict:
    """                                                                                                                                                                                                                                                                                                                                                                                
    Convert ECON-D Offline parameters to slow-control parameters used in SWAMP  
    * path_to_config : the location of the pedestals json file
    * mip_sf : a scaling factor in units of MIP to define the threshold
    * cmtype : 2, 4, all - the common mode type to use    
    The following ZS algorithms need to be programmed

    * Zero-supression: `A0_i + CE > (lamb x A_CM)>>5 + ((kappa_corr x Am1_i)>>5) + C_i`
    * Zero-suppresion BX-1: `Am1_i > (8 x Cm1_i) + ((betam1_corr x A_CM)>>5)`

    They require the following ROC event data:                                                                                                                                                                                                                                                                                                                                                                
    * `A0_i`: ADC from sensor channel i in BX=0                                                                                                                                                                                                                                                                                                                                       
    * `A_CM`: ADC from CM channel (or average of several CM channels)                                                                                                                                                                                                                                                                                                                 
    * `Am1_i`: ADC from sensor channel i in BX=–1                                                                                                                                                                                                                                                                                                                                     

    The programmable constants are:
    * CE: global                                                                                                                                                                                                                                                                                                                                                                    
    * lamb: per channel                                                                                                                                                                                                                                                                                                                                                             
    * C_i: per channel                                                                                                                                                                                                                                                                                                                                                              
    * Cm1_i: per channel                                                                                                                                                                                                                                                                                                                                                            
    * kappa_corr: per channel                                                                                                                                                                                                                                                                                                                                                       
    * betam1_corr: per channel
    """

    #the configuration registry map
    config_regmap = {}
    #read the pedestals json and iterate over modules
    input_json = json.loads('{"ped":"'+path_to_config+'"}')
    config = buildLevel0CalibParams(input_json, cmtype)

    for typecode_key, c_dict in config.items():
        # read offline calibration constants
        P_i = np.array(c_dict["ADC_ped"])
        P_cm = np.array(c_dict[f"CM_ped"])

        #if only pedestals+noise
        if onlyPedestals:
           beta_corr = np.zeros(len(c_dict[f"CM_slope"])) #beta = 0
           kappa_corr = np.zeros(len(c_dict["BXm1_slope"])) #kappa = 0
           noise = np.array(c_dict["Noise"])

           T = factor * noise
        elif P_CM_correction:
           beta_corr = np.array(c_dict[f"CM_slope"]) 
           kappa_corr = np.zeros(len(c_dict["BXm1_slope"])) #kappa = 0
           noise = np.array(c_dict["Noise"])

           T = np.array(c_dict["MIPS_scale"]) * mip_sf + factor * noise
        elif P_CM_BXm1_correction:
           beta_corr = np.ones(len(c_dict[f"CM_slope"])) #beta = 1
           kappa_corr = factor * np.ones(len(c_dict["BXm1_slope"])) #kappa = scan
           noise = np.array(c_dict["Noise"])
           T = np.ones(len(np.array(c_dict["MIPS_scale"])))
        else:
           kappa_corr = np.array(c_dict["BXm1_slope"])
           beta_corr = np.array(c_dict[f"CM_slope"])
           T = np.array(c_dict["MIPS_scale"]) * mip_sf

        #convert to ECOND ZS parameters
        lamb = beta_corr * (1 - kappa_corr)
        C_i = T + (1 - kappa_corr) * P_i + lamb * P_cm
        if onlyPedestals: #set to 0
           Tm1 = np.zeros(len(c_dict["MIPS_scale"]))
           betam1_corr = beta_corr.copy()
           Cm1_i = np.zeros(len( P_i))
        else:
           Tm1 = np.array(c_dict["MIPS_scale"]) * mip_sf_m1 / 8. # threshold in steps of 1/8
           betam1_corr = beta_corr.copy()
           Cm1_i = Tm1 + P_i + beta_corr * P_cm

        #digitize the floating point numbers
        #see Tables 23 and 24 of the ECON-D specification document
        def _digitizeVals(a_vals,dyn_range, nbits):
            max_digi = 2**nbits-1
            lsb = dyn_range / max_digi
            #to list is used to force native python int
            digivals = np.clip(a_vals/lsb, a_min=0, a_max=max_digi).astype(int).tolist()
            return digivals
        CE_int = _digitizeVals(CE, 1023, 10)
        lamb_int = _digitizeVals(lamb, 3.96875, 7)
        kappa_corr_int = _digitizeVals(kappa_corr, 1.96875, 6)
        C_i_int = _digitizeVals(C_i, 255, 8)
        Cm1_i_int = _digitizeVals(Cm1_i,120, 4)
        betam1_corr_int = _digitizeVals(betam1_corr, 3.96875, 7 ) 

        #build the register map
        c_regmap = {'ZSCommon_Global_zs_ce' : CE_int}

        #default routing of eRx's into CM processor
        route_erx = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        if cmtype == '2':
            #for CM2, change selection so that eRx 0 and 1 use CM_ROC0, etc
            #WARNING: CM2 will not work for neRx>6
            route_erx = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
        #convert routing array into register
        route_value = int(sum([(r << (4*j)) for j, r in enumerate(route_erx[::-1])]))
        # 32 bits LSB in 00
        c_regmap["ELinkProcessors_Global_cm_erx_route_00"] = (route_value & 0xffffffff)
        # 16 bits MSB in 01
        c_regmap["ELinkProcessors_Global_cm_erx_route_01"] = (route_value >> 32) & 0xffff

        for channel in c_dict["Channel"]:
 
            #each eRx handles data from 1 half of an HGCROC (37 sensor channels, 2 common mode channels)
            ch = channel % 37
            erx = int(channel / 37)
            #configure CM
            #default routing of eRx's into CM processor
            route_erx = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
            if cmtype == '4':
                #for CM4, change selection so that eRx 0 and 1 use CM_ROC0, eRx 1 and 2 use CM_ROC1, etc.
                c_regmap[f"ELinkProcessors_Global_cm_selection_x_{erx:02d}"] = int(erx/2)    
            elif cmtype == '2':
                #for CM2, change selection so that eRx 0 uses CM_ROC0, eRx 1 uses CM_ROC1, etc
                #for eRx > 5, will use CM_MOD
                c_regmap[f"ELinkProcessors_Global_cm_selection_x_{erx:02d}"] = int(erx) if erx <= 5 else 6
            else:
                #default value, indicates usage of CM_MOD
                c_regmap[f"ELinkProcessors_Global_cm_selection_x_{erx:02d}"] = 6

            #configure ZS
            c_regmap[f"ZS_{erx:02d}_zs_lambda_{ch:02d}"] = lamb_int[channel]
            c_regmap[f"ZS_{erx:02d}_zs_kappa_{ch:02d}"] = kappa_corr_int[channel]
            c_regmap[f"ZS_{erx:02d}_zs_c_i_{ch:02d}"] = C_i_int[channel]
            c_regmap[f"ZSmOne_{erx:02d}_zs_c_i_m_{ch:02d}"] = Cm1_i_int[channel]
            c_regmap[f"ZSmOne_{erx:02d}_zs_beta_m_{ch:02d}"] = betam1_corr_int[channel]
            
            # TODO : masks - should one use the Valid flags in the calibration json being processed?
            # TODO: set as input if channel is masked, masking takes priority over passing                                                                                                                                                                                                                                                                                             
            # mask: if set, nothing is readout for that channel (unless in pass through mode)                                                                                                                                                                                                                                                                                          
            # pass: forces the ADC/TOT to be readout for the channel, does not affect TOA to be transmitted                                                                                                                                                                                                                                                                            
            # c_regmap[f"ZS_{erx:02d}_zs_mask_i_{ch:02d}"] = 0                                                                                                                                                                                                                                                                                                                         
            # c_regmap[f"ZS_{erx:02d}_zs_pass_i_{ch:02d}"] = 0                                                                                                                                                                                                                                                                                                                         

            # TODO: determine if channel is masked                                                                                                                                                                                                                                                                                                                                     
            # passm1: forces ADC[-1] to be readout for the channel, does not affect TOA to be transmitted                                                                                                                                                                                                                                                                              
            # c_regmap[f"ZSmOne_{erx:02d}_zs_pass_i_{ch:02d}"] = 0                                                                                                                                                                                                                                                                                                                     
            # c_regmap[f"ZSmOne_{erx:02d}_zs_mask_i_{ch:02d}"] = 0                                                                                                                                                                                                                                                                                                                     

        config_regmap[typecode_key] = c_regmap

    return config_regmap


def main():

    #parse arguments and add as class attributes
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input",
                        help='input json file with pedestal measurements=%(default)s',
                        default="data/level0_calib_params_TB2024v2.json")
    parser.add_argument("--mipSF",
                        help='mip scaling factor to determine ZS threshold %(default)s',
                        default=1.0, type=float)
    parser.add_argument("--mipSFm1",
                        help='mip scaling factor to determine ZS threshold for BX-1 %(default)s',
                        default=0.0, type=float)
    parser.add_argument("--CE",
                        help='global offset %(default)s',
                        default=0, type=float)
    parser.add_argument("--cmType",
                        help='CM type %(default)s',
                        default='2', type=str)
    parser.add_argument("-o", "--output",
                        help='output file (if not given, the input will be appended with "_econdzsreg") %(default)s',
                        default='', type=str)
    parser.add_argument("-oP", "--onlyPedestals",
                        help='correct only using Pedestal + noise',
                        default=False, type=bool)
    parser.add_argument("-CM", "--P_CM_correction",
                        help='scan for correcting only using Pedestal + Common mode ',
                        default=False, type=bool)
    parser.add_argument("-BX", "--P_CM_BXm1_correction",
                        help='scan for correcting using Pedestal + Common mode + BX-1 ',
                        default=False, type=bool)
    parser.add_argument("-F", "--factor",
                        help='factor for scan: factor * noise',
                        default=1, type=int)
    args = parser.parse_args()
    
    #build input for ECON-D configuration of the ZS processor
    econd_cfg = fillECONDconfig(path_to_config=args.input, 
                                CE = args.CE,
                                mip_sf=args.mipSF,
                                mip_sf_m1=args.mipSFm1,
                                cmtype=args.cmType,                                
                                onlyPedestals = args.onlyPedestals,
                                P_CM_BXm1_correction = args.P_CM_BXm1_correction,
                                P_CM_correction = args.P_CM_correction,
                                factor = args.factor)

    #save to file
    outurl = args.output
    if len(outurl)==0:
        outurl = args.input.replace('.json','_econzsreg.json')
    with open(outurl, "w") as fout:
        json.dump(econd_cfg, fout,  indent = 4)
    print(f'ECON-D ZS register configuration has been stored in {outurl}')

if __name__ == "__main__":
    sys.exit(main())
