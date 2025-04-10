import os, sys
import argparse
import json
import glob
import importlib
import pandas as pd

# import common HGCalCommissioning tools
sys.path.append("./")
try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *

# dictionary between run type and HGCalCalibration class
calibclass_dict = {
  'pedestal':        'Pedestals',
  #'CalPulse_scan':   'CalPulseScan',
  'trim_inv_scan':   'TrimInvScan',
  'vref_inv_scan':   'VRefScan',
  'vref_noinv_scan': 'VRefScan',
}

class HGCalCalibrationManager:
    
    def __init__(self):
        """Constructor of HGCalCalibrationManager class."""
        
        # parse arguments and add as class attributes
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', "--input", default="hgcal-sysval-offline/data/runregistry.feather",
                            help="input run registry file=%(default)r")
        parser.add_argument('-o', "--output", default="output", #required=True,
                            help='output directory')
        parser.add_argument('-r', "--reference", default="0000010151",
                            help="reference/relay number")
        parser.add_argument('-p', "--modargs", default="",
                            help="command line arguments to pass to calibration module, e.g. -p='--skipHistoFiller'")
        cmdargs = parser.parse_args()
        print(cmdargs)
        
        # open run registry
        df = pd.read_feather(cmdargs.input)
        
        # select entries that match reference
        df = df[df['Reference']==cmdargs.reference]
        
        # get the status and the dictionary defining the job
        scan_status, scan_map = self.getScanInputs(df)
        if not scan_status:
            print(f'[WARNING] Run type {cmdargs.reference} seems not complete, skipping it!')
            return
        
        # extract the calibration type and load module that handles it
        runtype = df['Type'].iloc[-1]
        calibclass = calibclass_dict[runtype]
        if not calibclass:
            print(f'[WARNING] Run type {runtype} is not supported by HGCalCalibrationManager, skipping it!')
            return
        
        # prepare scan map
        outputdir = f'{cmdargs.output}/{runtype}/Relay{cmdargs.reference}'
        os.makedirs(outputdir, exist_ok=True)
        print(f'Output directory is now {outputdir}')
        scan_map_json = f'{outputdir}/scan_map.json'
        saveAsJson(scan_map_json,scan_map)
        
        # call calibration module
        print(f'Scan map defined @ {scan_map_json}')
        calib_module_args = ['--scanmap',scan_map_json,'-o',outputdir,'--forceRewrite']
        if cmdargs.modargs:
            calib_module_args += cmdargs.modargs.split(' ')
        calib_module_name = f'HGCal{calibclass}'
        calib_module = importlib.import_module(calib_module_name)
        print(f'Launching {calib_module_name} with cmdargs={calib_module_args}')
        calib_impl = getattr(calib_module,calib_module_name)(calib_module_args,runtype=runtype) # run
        # TODO: convert JSON from calib_impl.jsonurl to YAML


    def parseScanPointInfo(self, runtype : str, scan_point : dict):
        """This method retrieves only the parameters that really matter from the scan_point dictionary
        depending on the run type. If runtype is not recognized an empty dict is returned."""
        scan_param_dict = {}
        if runtype=='trim_inv_scan':
            scan_param_dict = {
              "trim_inv": scan_point['roc']['HalfWise']['0']['trim_inv']
            }
        elif runtype in ['vref_inv_scan','vref_noinv_scan']:
            # workaround: convert channel list to a CSV string because RDF FromSpec cannot handle a list...
            injChans = ','.join(str(k) for k in scan_point['roc']['ch'].keys())
            scan_param_dict = {
              "InjChans":   injChans, # e.g. "17,53"
              "TargetADC":  300, # target ADC   
              "Inv_vref":   scan_point['roc']['ReferenceVoltage']['0'].get('Inv_vref',0),
              "Noinv_vref": scan_point['roc']['ReferenceVoltage']['0'].get('Noinv_vref',0),
            }
        return scan_param_dict


    def getScanInputs(self, ref_df : pd.DataFrame):
        """
        This method loops over the runs belonging to the same reference.
        assumes that `ref_df` is already filtered for the reference of interest
        in case of multiple entries only the last one is used.
        the last report in the 'Reports' column is used to retrieve the information on the output directory
        then the job report is read and used to retrieve the information about which scan point does each run match to
        finally a dict { Run : int : { 'idx' : scan_index : int, 'files': nanoaod : list, 'params': params ; dict} }
        is filled and returned for the analysis to start.
        """
        
        scan_inputs = {}
        total_scan_points_exp = 0
        for run, group in ref_df.groupby('Run'):
            #print(run)
            mask = (group['Ended']==True) & (group['Reports'].str.len()>0)
            if mask.sum()==0: continue
            last_entry_report = json.loads(group[mask].iloc[-1]['Reports'][0])
            nanodir = last_entry_report['Output']
            jobreport = glob.glob(f'{nanodir}/reports/job*{run}*.json')[0]
            
            with open(jobreport,'r') as stream:
                jobcfg = json.load(stream)
                if not 'scan_point' in jobcfg:
                    continue
                runtype = jobcfg['type']
                scan_point_dict = jobcfg['scan_point']
                scan_idx = scan_point_dict.pop('scan_idx')
                total_scan_points_exp = scan_point_dict.pop('total_scan_pts')
            
            scan_inputs[str(run)] = {
                'idx' : scan_idx,
                'input' : glob.glob(f'{nanodir}/NANO*{run}*.root'),
                'params' : self.parseScanPointInfo(runtype,scan_point_dict)
            }
        
        # check what has been collected
        total_scan_points=len(scan_inputs)
        if total_scan_points_exp==0:
            print('No compatible scan points found in job reports')
        elif total_scan_points_exp!=total_scan_points:
            print(f'Expected {total_scan_points_exp} but collected {total_scan_points} points from scan')
        else:
            print(f'Collected {total_scan_points} points')

        return (total_scan_points_exp==total_scan_points), scan_inputs


        
if __name__ == '__main__':
    manager = HGCalCalibrationManager()
