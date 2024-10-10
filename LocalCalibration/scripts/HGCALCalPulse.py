import sys
sys.path.append("./")
from HGCALCalibration import HGCALCalibration
import DigiAnalysisUtils as DAU
import HexPlotUtils as HPU
import numpy as np
import os
import ROOT
import pandas as pd
try:
  from HGCalCommissioning.LocalCalibration.CalPulseModel import CalPulseModel
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from CalPulseModel import CalPulseModel
  from JSONEncoder import *

class HGCALCalPulse(HGCALCalibration):

    def __init__(self):
        super().__init__()
        
    def addCommandLineOptions(self,parser):
        """Add specific command line options for pedestals."""
        #parser.add_argument("--injChans", nargs='+',
        #                    help="injected channels")
        parser.add_argument("--skipFits", action='store_true',
                            help="skip fits and use results already stored in the feather files")
        parser.add_argument("--addControlPlots", action='store_true',
                            help="add control plots for scan")
        
    @staticmethod
    def histofiller(args):
        """Customize the base histo filler from the digi analysis utils."""
        outdir, module, task_spec, cmdargs = args
        filter_conds = { '': "HGCMetaData_trigType==2" }
        status = DAU.scanHistoFiller(outdir, module, task_spec, filter_conds, verb=cmdargs.verbosity)
        return status
        
    @staticmethod
    def analyze(args):
        """Profiles the Channel vs ADC vs CM histogram to find pedestals to use."""

        typecode, url, cmdargs = args

        hnames = ['adc','tot']
        routput = DAU.profile3DScanHisto(url,hnames,storehists=cmdargs.addControlPlots,
                                         adc_cut=180,verb=cmdargs.verbosity)

        #read the summary (pandas)
        fit_out = os.path.dirname(routput) + f'/{typecode}_fits'
        if not cmdargs.skipFits:
          df = pd.read_feather(routput.replace('.root','.feather'))
          cpm = CalPulseModel(df,fit_out=fit_out)
          fit_results=cpm.fit_results
        else:
          fit_results = pd.read_feather(fit_out+'.feather')
          
        return {'Typecode':typecode,'Fits':fit_results}
    
    def createCorrectionsFile(self, results):
        """Final tweaks of the analysis results to export as a json file for CMSSW."""

        
        correctors={}
        popts = ['adc2fC','adc0','tot2fC','tot0','totlin','a']
        for r in results:

          typecode = r.pop('Typecode')
          fit_results = r['Fits']
          nerx = fit_results['erx'].max()+1
          avg_module = fit_results[popts].agg(np.average)
          
          r_corrections = dict( [(p,[]) for p in popts] )
            
          #loop over erx
          for ierx in range(nerx):
            mask = (fit_results['erx']==ierx)
            group = fit_results[mask]
            
            #start by preparing the average
            if mask.sum()>0:
              avg_erx = group[popts].agg(np.average)
            else:
              avg_erx = avg_module

            #loop over the channels
            for ich in range(37):
              mask_ch = (group['channel']==ich+37*ierx)
              if mask_ch.sum()==1:
                row_ch = group[mask_ch][popts].iloc[0]
              else:
                row_ch = avg_erx

              #add final channel parameter to the corrections
              for p in popts:
                r_corrections[p].append( row_ch[p] )

          #add to the final list of corrections
          correctors[typecode]=r_corrections
            
        #export final result
        jsonurl = f'{self.cmdargs.output}/calpulse.json'
        saveAsJson(jsonurl, correctors)

        #do hexplots if required
        if self.cmdargs.doHexPlots:
          rooturl = f'{self.cmdargs.output}/calpulse_hexplots.root'
          HPU.createCalibHexPlotSummary(jsonurl,rooturl)

        return jsonurl
          

if __name__ == '__main__':
    pedestal = HGCALCalPulse()
    
