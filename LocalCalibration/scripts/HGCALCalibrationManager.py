import os
import sys
sys.path.append("./")
import argparse
import pandas as pd
import json
import glob
import importlib
try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *

class HGCALCalibrationManager:

    def __init__ (self):
        """Constructor of HGCALCalibrationManager class"""

        #parse arguments and add as class attributes
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--input",
                            help='input run registry file=%(default)',
                            default="hgcal-sysval-offline/data/runregistry.feather", type=str)
        parser.add_argument("-o", "--output",
                            help='output directory', type=str, required=True)
        parser.add_argument("-r", "--reference",
                            help='reference number',
                            default="0000010151", type=str)
        cmdargs = parser.parse_args()

        #open run registry
        df = pd.read_feather(cmdargs.input)

        #select entries that match reference
        df = df[df['Reference']==cmdargs.reference]

        #get the status and the dictionary defining the job
        scan_status, scan_map = self.getScanInputs(df)
        if not scan_status:
            print(f'[WARNING] Run type {run_type} Ref {cmdargs.reference} seems not complete, skipping it!')
            return -1
        
        #extract the calibration type and load module that handles it
        run_type = df['Type'].iloc[-1]
        calib_type_map = {'pedestal': 'Pedestals', 'trim_inv_scan': 'TrimInvScan'}
        calib_type = calib_type_map[run_type]
        if not calib_type:
            print(f'[WARNING] Run type {run_type} is not supported by HGCALCalibrationManager, skipping it!')
            return -1

        outputdir = f'{cmdargs.output}/{run_type}/Relay{cmdargs.reference}'
        os.makedirs(outputdir, exist_ok=True)
        print(f'Output directory is now {outputdir}')
        scan_map_json = f'{outputdir}/scan_map.json'
        saveAsJson(scan_map_json,scan_map)
        print(f'Scan map defined @ {scan_map_json}')
        calib_module_args = ['--scanmap',scan_map_json,'-o',outputdir,'--forceRewrite'] #, '--skipHistoFiller']
        calib_module_name = f'HGCAL{calib_type}'
        calib_module = importlib.import_module(calib_module_name)
        print(f'Launching {calib_module_name} with args={calib_module_args}')
        calib_impl = getattr(calib_module,calib_module_name)(calib_module_args)


    def parseScanPointInfo(self, runtype : str, scan_point : dict) :
        """this method retrieves only the parameters that really matter from the scan_point dictionary
        depending on the run type. If runtype is not recognized an empty dict is returned"""
        
        scan_param_dict = {}
        
        if runtype=='trim_inv_scan':
            scan_param_dict = {"trim_inv":scan_point['roc']['HalfWise']['0']['trim_inv']}
            
        return scan_param_dict


    def getScanInputs(self, ref_df : pd.DataFrame):
        """this method loops over the runs belonging to the same reference.
        assumes that `ref_df` is already filtered for the reference of interest
        in case of multiple entries only the last one is used.
        the last report in the 'Reports' column is used to retrieve the information on the output directory
        then the job report is read and used to retrieve the information about which scan point does each run match to
        finally a dict { Run : int : { 'idx' : scan_index : int, 'files': nanoaod : list, 'params': params ; dict} }
        is filled and returned for the analysis to start
        """
    
        scan_inputs = {}
        total_scan_points_exp = 0
        for run, group in ref_df.groupby('Run'):

            mask = (group['Ended']==True) & (group['Reports'].str.len()>0)
            last_entry_report = json.loads(group[mask].iloc[-1]['Reports'][0])
            nanodir = last_entry_report['Output']
            jobreport = glob.glob(f'{nanodir}/reports/job*{run}*.json')[0]

            with open(jobreport,'r') as stream:
                jobcfg = json.load(stream)
                if not 'scan_point' in jobcfg:
                    continue
                scantype = jobcfg['type']
                scan_point_dict = jobcfg['scan_point']
                scan_idx = scan_point_dict.pop('scan_idx')
                total_scan_points_exp = scan_point_dict.pop('total_scan_pts')

            scan_inputs[str(run)] = {
                'idx' : scan_idx,
                'input' : glob.glob(f'{nanodir}/NANO*{run}*.root'),
                'params' : self.parseScanPointInfo(scantype,scan_point_dict)
            }

        #check what has been collected
        total_scan_points=len(scan_inputs)
        if total_scan_points_exp==0:
            print('No compatible scan points found in job reports')
        elif total_scan_points_exp!=total_scan_points:
            print(f'Expected {total_scan_points_exp} but collected {total_scan_points} points from scan')
        else:
            print(f'Collected {total_scan_points} points')

        return (total_scan_points_exp==total_scan_points), scan_inputs


        
if __name__ == '__main__':
    HGCALCalibrationManager()
