import sys
sys.path.append("./")
from HGCALCalibration import HGCALCalibration
import DigiAnalysisUtils as DAU
import HexPlotUtils as HPU
import numpy as np
try:
    from HGCalCommissioning.LocalCalibration.JSONEncoder import getCalibTemplate
except ImportError:
    sys.path.append('./python/')
    from JSONEncoder import getCalibTemplate

class HGCALPedestals(HGCALCalibration):

    def __init__(self):
        self.histofiller = self.pedestalHistoFiller
        super().__init__()

    @staticmethod
    def pedestalHistoFiller(args):
        """costumize the base histo filler from the digi analysis utils"""
        histoBinDefs = DAU._baseHistoBinDefs.copy()
        histoBinDefs['adcvscm'] = (1024,-0.5,1023.5,200,149.5,349.5)
        return DAU.baseHistoFiller(args,binDefs=histoBinDefs)
        
    def addCommandLineOptions(self,parser):
        """add specific command line options for pedestals"""
        parser.add_argument("-g", "--gain",
                            help='gain (this is to be deprecated once info is in NANO)=%(default)s',
                            default=160, type=int)
        parser.add_argument("--doHexPlots",
                            action='store_true',
                            help='save hexplots for the pedestals')
        

    def buildScanParametersDict(self,file_list,module_list):
        """a simple pedestal analysis doesn't have any parameters scanned, return lists of empty dicts"""

        nfiles = len(file_list)
        
        scanparams={}
        for m in module_list:
            scanparams[m] = [
                {} for i in range(nfiles)
            ]
        
        return scanparams

    @staticmethod
    def analyze(args):
        """profiles the Channel vs ADC vs CM histogram to find pedestals to use"""
        typecode, url, cmdargs = args
        results = DAU.profile3DHisto(url,'adcvscm')

        #fix the number of e-Rx should not be hardcoded
        cor_values = getCalibTemplate(nch = len(results['X']) )
        cor_values['Typecode']=typecode.replace('_','-')
        gain2idx={80:0,160:1,320:2}
        idx = gain2idx[cmdargs.gain]
        cor_values['ADC_ped'][idx]=results['Y_mean']
        sadc = np.array(results['Y_rms'])
        cor_values['CM_ped'][idx]=results['Z_mean']
        scm = np.array(results['Z_rms'])
        r = np.array(results['YZ_rho'])
        noslope = np.zeros_like(r)
        cor_values['CM_slope'][idx] = np.where(scm>1e-3, r*sadc/scm, noslope).tolist()
        cor_values['Noise'][idx]=sadc.tolist()
        cor_values['Valid'] = (sadc>1e-3).astype(int).tolist()
        return cor_values


    def createCorrectionsFile(self, results):
        
        """ final tweaks of the analysis results to export as a json file for CMSSW """

        jsonurl = f'{self.output}/pedestals_{self.gain}fC.json'
        correctors={}
        for r in results:
            typecode = r.pop('Typecode')
            correctors[typecode]=r
        DAU.saveAsJson(jsonurl, correctors, compress=False)

        if self.doHexPlots:
            rooturl = f'{self.output}/pedestals_{self.gain}fC_hexplots.root'
            HPU.createCalibHexPlotSummary(jsonurl,rooturl)
            
        return jsonurl

if __name__ == '__main__':

    pedestal = HGCALPedestals()
