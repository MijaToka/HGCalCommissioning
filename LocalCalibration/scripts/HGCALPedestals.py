import sys
sys.path.append("./")
from HGCALCalibration import HGCALCalibration
import DigiAnalysisUtils as DAU
import HexPlotUtils as HPU
import numpy as np

try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *

class HGCALPedestals(HGCALCalibration):

    def __init__(self):
        self.histofiller = self.pedestalHistoFiller
        super().__init__()

    @staticmethod
    def pedestalHistoFiller(args):
        """costumize the base histo filler from the digi analysis utils"""

        outdir, module, task_spec, cmdargs = args

        status = False
        if cmdargs.fromNZSsampling or cmdargs.scan:
            filter_conds = {'rnd':'HGCMetaData_trigType==4'}
            if cmdargs.fromNZSsampling:
                filter_conds = {
                    'zs':'HGCMetaData_trigType==4',
                    'nzs':'HGCMetaData_trigType==16'
                }
            status = DAU.scanHistoFiller(outdir, module, task_spec, filter_conds)
        else:
            filter_cond = 'HGCMetaData_trigType==4' #request randoms only
            status = DAU.analyzeSimplePedestal(outdir, module, task_spec, filter_cond)

        return status
        
    def addCommandLineOptions(self,parser):
        """add specific command line options for pedestals"""
        parser.add_argument("--doHexPlots",
                            action='store_true',
                            help='save hexplots for the pedestals')
        parser.add_argument("--fromNZSsampling",
                            action='store_true',
                            help='pedestals are to be derived from a sample with NZS sampling')
        parser.add_argument("--scan",
                            action='store_true',
                            help='analyze a scan')
        

    def buildScanParametersDict(self,file_list,module_list):
        """for now, returns a list of empty dicts"""

        nfiles = len(file_list)
        
        scanparams={}
        for m in module_list:
            scanparams[m] = [
                {} for i in range(nfiles)
            ]
        
        return scanparams

    @staticmethod
    def analyze(args):
        typecode, url, cmdargs = args
        if cmdargs.fromNZSsampling:
            pedestals_dict = HGCALPedestals.analyzeNZSsamplingResults(args)
        else:
            pedestals_dict = HGCALPedestals.analyzeSimplePedestalResults(args)
        return pedestals_dict

    @staticmethod
    def analyzeNZSsamplingResults(args):
        typecode, url, cmdargs = args
        pedestals_dict = {'Typecode':typecode}
        return pedestals_dict

    @staticmethod
    def analyzeSimplePedestalResults(args):
        
        """profiles the Channel vs ADC vs CM histogram to find pedestals to use"""
        
        typecode, url, cmdargs = args
        pedestals_dict = {'Typecode':typecode}

        for x in ['adcm1','cm2','cm4','cmall']:
            results = DAU.profile3DHisto(url,f'adcvs{x}')
            
            x_rms = np.array(results['Y_rms'])
            adc_rms = np.array(results['Z_rms'])
            rho = np.array(results['YZ_rho'])
            noslope = np.zeros_like(rho)

            pedestals_dict[x+'_ped'] = results['Y_mean']
            pedestals_dict[x+'_rms'] = x_rms.tolist()
            pedestals_dict[f'{x}_slope'] = np.where(x_rms>1e-3, rho*adc_rms/x_rms, noslope).tolist()
            
            if 'ADC_ped' in pedestals_dict: continue
            pedestals_dict['ADC_ped']=results['Z_mean']
            pedestals_dict['ADC_rms']=adc_rms.tolist()
            pedestals_dict['Valid'] = (adc_rms>1e-3).astype(int).tolist()
            pedestals_dict['Channel'] = [i for i in range(adc_rms.shape[0])]

        return pedestals_dict

    
    def createCorrectionsFile(self, results):
        
        """ final tweaks of the analysis results to export as a json file for CMSSW """

        correctors={}
        for r in results:
            typecode = r.pop('Typecode')
            correctors[typecode]=r
        jsonurl = f'{self.cmdargs.output}/pedestals.json'
        saveAsJson(jsonurl, correctors)

        if self.cmdargs.doHexPlots:
            rooturl = f'{self.cmdargs.output}/pedestals_hexplots.root'
            HPU.createCalibHexPlotSummary(jsonurl,rooturl)
            
        return jsonurl

if __name__ == '__main__':

    pedestal = HGCALPedestals()
