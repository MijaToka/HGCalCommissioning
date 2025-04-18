import sys
import glob
import yaml
import re
import numpy as np
import os
import ROOT
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import mplhep as hep
plt.style.use(hep.style.CMS)

# import common HGCalCommissioning tools
import DigiAnalysisUtils as DAU
try:
  from HGCalCommissioning.LocalCalibration.HGCalCalibration import HGCalCalibration
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from HGCalCalibration import HGCalCalibration
  from JSONEncoder import *

class HGCalTrimInvScan(HGCalCalibration):
    
    def __init__(self, raw_args=None, runtype='trim_inv_scan', scanparam='trim_inv'):
        self.histofiller = DAU.adcScanHistoFiller
        super().__init__(raw_args, runtype=runtype, scanparam=scanparam)

    def addCommandLineOptions(self, parser):
        """Add specific command line options for the VRef scan"""
        super().addCommandLineOptions(parser)
    
    @staticmethod
    def analyze(args):
        """
        Profiles the Channel vs ADC vs CM histogram to find pedestals
        to use the fit results are stored visually in a PDF file.
        """

        typecode, url, cmdargs = args

        #prepare for plotting if required
        doPlots = cmdargs.doControlPlots
        if doPlots:
          plt.style.use(hep.style.CMS)
          pdf_url = url.replace('.root','_fits.pdf')
          pdf = PdfPages(pdf_url)
        
        # model for <adc> vs <trim_inv> in each channel
        trim_inv_model = lambda x,a,b : a*x+b
        
        # loop over channels and fit
        fIn = ROOT.TFile.Open(url)
        
        chTypeprofile = fIn.Get('chType')
        scaninfo = fIn.Get('scaninfo')
        npts = scaninfo.GetNbinsX()
        x = np.array([scaninfo.GetBinContent(ipt+1,2) for ipt in range(npts)]) 

        adcprofile = fIn.Get('adcprofile')
        adcprofile.SetErrorOption('s')
        nch = adcprofile.GetNbinsY()

        modulecmprofile = fIn.Get('modulecmprofile')
        modulecmprofile.SetErrorOption('s')

        nerx = int(nch/37)
        fit_results = []
        for ierx in range(nerx):
          
          choffset = ierx*37+1
          
          if doPlots:
            fig, ax = plt.subplots(7,6,figsize=(18,28),sharex=True,sharey=True)
          
          for ich in range(-1, 37):
            chType = 2 if (ich == -1) else chTypeprofile.GetBinContent(ich+choffset) # 0: calibration, 1: channel, 2: common mode
            profile = modulecmprofile if ich == -1 else adcprofile
            y = np.array([profile.GetBinContent(ipt+1,ich+choffset) for ipt in range(npts)])
            yerr = np.array([profile.GetBinError(ipt+1,ich+choffset) for ipt in range(npts)])
            
            # fit the model
            try:
                popt, pcov = curve_fit(trim_inv_model, x, y, sigma=yerr)
                popt_unc = np.sqrt(np.diag(pcov))
                yexp = trim_inv_model(x,*popt)
                chi2 = (((y-yexp)/yerr)**2).sum()
                ndof = len(x)-len(popt)
                fit_results.append( [ierx, ich+choffset-1, popt[0], popt_unc[0], popt[1], popt_unc[1], chi2/ndof, True, chType] )
            except Exception as e:
                print(e)
                fit_results.append( [ierx, ich+choffset-1] + [-1]*5 + [False]+ [chType] )
            
            # show the fit result
            if not doPlots: continue
            #ix = ich%ax.shape[0]
            #iy = int(ich/ax.shape[0])
            if ich == -1:
                ix, iy = ax.shape[0] - 1, ax.shape[1] - 1
            else:
                ix = ich % ax.shape[0]
                iy = int(ich / ax.shape[0])
            ax[ix,iy].grid()
            ax[ix,iy].errorbar(x,y,yerr=yerr,marker='o',elinewidth=1,capsize=1,color='k',ls='none')
            txtargs = { 'transform':ax[ix,iy].transAxes, 'fontsize':12 }
            if fit_results[-1][-2]:
                ax[ix,iy].plot(x,yexp,ls='-')
                channel_name = "CM channel" if ich == -1 else f'Channel {ich+choffset}'
                ax[ix,iy].text(0.1,0.90, channel_name, **txtargs)
                #ax[ix,iy].text(0.1,0.9,f'Channel {ich+choffset}', **txtargs)
                ax[ix,iy].text(0.1,0.85,rf'Slope= ${popt[0]:3.2f} \pm {popt_unc[0]:3.2f}$', **txtargs)
                ax[ix,iy].text(0.1,0.80,rf'Offset = ${popt[1]:3.2f} \pm {popt_unc[1]:3.2f}$', **txtargs)
                ax[ix,iy].text(0.1,0.75,rf'$\chi^2/dof={chi2:3.2f}/{ndof}$', **txtargs)
            else:
                ax[ix,iy].text(0.1,0.90,f'Channel {ich+choffset} fit failed', **txtargs, bbox={'facecolor':'red', 'alpha':0.5})
          
          # finalize page
          if doPlots:
              plt.subplots_adjust(wspace=0, hspace=0)
              pdf.attach_note(f'Fits to channels in e-Rx {ierx+1}')
              pdf.savefig()
              plt.close()
        
        # convert to a pandas for further manipulation
        fit_results = pd.DataFrame(
          fit_results,
          columns = ['ierx','ich','slope','slope_unc','offset','offset_unc','reduced_chi2','valid','chType']
        )
        
        # determine the max offset per erx
        # start by determining the median and the standard deviation (s.d.)
        # determine max offset from fit which are within 2-s.d. of the median
        mask_valid = (fit_results['valid']==True)
        criteria = fit_results[mask_valid].groupby('ierx')['offset'].agg(['median','std']).to_dict()
        median_offset = fit_results['ierx'].map(criteria['median'])
        std_offset = fit_results['ierx'].map(criteria['std'])
        fit_matches_criteria = (np.abs(fit_results['offset']-median_offset)<2*std_offset)        
        maxoffset_per_erx = fit_results[mask_valid & fit_matches_criteria].groupby('ierx')['offset'].agg('max').to_dict()
        fit_results['max_offset'] = fit_results['ierx'].map(maxoffset_per_erx)
        
        # determine the best trim_inv per channel (clip to 6b DAC = [0,64[ and round to integer)
        fit_results['trim_inv_optim'] = np.rint( np.clip(
          (fit_results['max_offset']-fit_results['offset'])/fit_results['slope'],
          0, 64
        ) )
        
        # do some histogramming as summary
        if doPlots:
            fig, ax = plt.subplots(3,2,figsize=(18,28))          
            offsetbins = np.linspace(fit_results[mask_valid]['offset'].min(),fit_results[mask_valid]['offset'].max(),20)
            slopebins = np.linspace(fit_results[mask_valid]['slope'].min(),fit_results[mask_valid]['slope'].max(),20)
            triminvbins = np.linspace(fit_results[mask_valid]['trim_inv_optim'].min(),fit_results[mask_valid]['trim_inv_optim'].max(),20)
            chi2bins = np.linspace(fit_results[mask_valid]['reduced_chi2'].min(),fit_results[mask_valid]['reduced_chi2'].max(),20)
            for ierx, group in fit_results[mask_valid].groupby('ierx'):
                hargs = {'lw':3, 'histtype':'step', 'label':f'eRx {ierx}'}
                ax[0][0].hist( group['offset'],**hargs,bins=offsetbins)
                ax[1][0].hist( group['slope'],**hargs,bins=slopebins)
                ax[1][1].hist( group['trim_inv_optim'], **hargs,bins=triminvbins)
                ax[2][0].hist( group['reduced_chi2'],**hargs,bins=chi2bins)
            
            ax[0][0].set_xlabel('Offset')
            ax[1][0].set_xlabel('Slope')
            ax[1][1].set_xlabel('Optimized trim_inv')
            ax[2][0].set_xlabel(r'$\chi^2/dof$')
            for i in range(3):
                ax[i][0].grid()
                ax[i][1].grid()
                ax[i][0].legend()
            
            ax[0][1].plot(fit_results[mask_valid]['ierx'],fit_results[mask_valid]['max_offset'],lw=3)
            ax[0][1].set_xlabel('eRx')
            ax[0][1].set_ylabel('max offset')
            ax[2,1].set_axis_off()
            
            pdf.attach_note(f'Summary for {typecode}')
            pdf.savefig()
            plt.close()
            pdf.close()
            print(f'Fit results pictures stored in {pdf_url}')
        
        # all done here
        fIn.Close()
        return {'Typecode':typecode,'Fits':fit_results}
        
    
    @staticmethod
    def producePlots(typecode, url, cmdargs, fileIn, df_fitres):
        """Produce control plots."""
        pass
    
    def createCorrectionsFile(self, results):
        """Final tweaks of the analysis results to export as json."""
        corr_dict = {}
        for entry in results:
            typecode, fits = entry['Typecode'], entry['Fits']
            fits_cm = fits[fits['chType'] == 2].reset_index()
            fits_cm['trim_inv'] = fits_cm['trim_inv_optim'].fillna(0).astype('int').clip(upper=63)
            corr_dict[typecode] = {'ierx': fits_cm['ierx'].tolist(), 'trim_inv_cm': fits_cm['trim_inv'].tolist()}
            fits_ch = fits[fits['chType'] != 2].reset_index()
            fits_ch['trim_inv'] = fits_ch['trim_inv_optim'].fillna(0).astype('int').clip(upper=63)
            corr_dict[typecode].update({'Channel': fits_ch['ich'].tolist(), 'trim_inv': fits_ch['trim_inv'].tolist()})
        jsonurl = f'{self.cmdargs.output}/triminvscan.json'
        saveAsJson(jsonurl, corr_dict)
        return jsonurl
        

if __name__ == '__main__':
    scan = HGCalTrimInvScan()
