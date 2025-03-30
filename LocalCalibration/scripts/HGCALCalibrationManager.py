import os
import sys
sys.path.append("./")
import argparse
import pandas as pd

class HGCALCalibrationManager:

    def __init__ (self):
        """Constructor of HGCALCalibrationManager class"""

        #parse arguments and add as class attributes
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--input",
                            help='input run registry file=%(default)',
                            default="hgcal-sysval-offline/data/runregistry.feather", type=str)
        parser.add_argument("-r", "--reference",
                            help='reference number',
                            default="0000010151", type=str)
        cmdargs = parser.parse_args()

        #open run registry
        df = pd.read_feather(cmdargs.input)

        #select entries that match reference
        df = df[df['Reference']==cmdargs.reference]

        #extract the calibration type
        run_type = df['Type'].iloc[0]
        calib_type_map = {'pedestal': 'Pedestals', 'trim_inv_scan': 'TrimInvScan'}
        calib_type = calib_type_map[run_type]
        if not calib_type:
            print(f'[WARNING] Run type {run_type} is not supported by HGCALCalibrationManager, skipping it!')
            return

        #load the module
        module_name = f'HGCAL{calib_type}'
        print(f'scripts.{module_name}')
        module = getattr(__import__(f'scripts.{module_name}', fromlist=[module_name]), module_name)

        #create the json
        data = {run:{} for run in df['Run']}
        filename = module.create_json(data)

        #run module
        os.system(f'python3 scripts/{module_name}.py --relaymap {filename}')

if __name__ == '__main__':
    HGCALCalibrationManager()
