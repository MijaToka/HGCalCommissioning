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

try:
  from HGCalCommissioning.LocalCalibration.HGCALCalibration import HGCALCalibration
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
  from HGCalCommissioning.LocalCalibration.DigiAnalysisUtils import *
except ImportError:
  sys.path.append('./python/')
  from HGCALCalibration import HGCALCalibration
  from JSONEncoder import *
  from DigiAnalysisUtils import *


class HGCALTrimInvScan(HGCALCalibration):

    def __init__(self, raw_args=None):
        super().__init__(raw_args)
        
    def addCommandLineOptions(self,parser):
        """Add specific command line options for the trim_inv_scan"""
        parser.add_argument("--disableControlPlots", action='store_true', help="disable control plots for scan")
        return
            
    
    @staticmethod
    def histofiller(args):
        """Customize the base histo filler from the digi analysis utils."""
        outdir, module, task_spec, cmdargs = args

        ix_filt=-1
        if ':' in task_spec:
            task_spec, ix_filt = task_spec.split(':')
    
        # read #pts and #eErx from first task
        with open(task_spec) as json_data:
            samples = json.load(json_data)['samples']
    
        npts = max(d['metadata']['index'] for s, d in samples.items())
        nerx = samples['data1']['metadata']['nerx']
        nch = nerx*37
    
        # fill a histo with the scan info
        scantype = samples['data1']['metadata']['type'] # automatically recognize scan type
        ptbins = (npts,0.5,npts+0.5) # scan points
        scanInfoHist = ROOT.TH2F('scaninfo', f"{scantype} info;Scan point;Parameters", *ptbins, 3,0,3)
        scanInfoHist.GetYaxis().SetBinLabel(1,'ScanPoint')
        scanInfoHist.GetYaxis().SetBinLabel(2,'trim_inv')
        scanInfoHist.GetYaxis().SetBinLabel(3,'n')        
        for key, sample in samples.items(): # loop over scan points
            idx  = sample['metadata']['index']
            trim_inv = sample['metadata']['trim_inv']
            flist = sample['files']
            scanInfoHist.SetBinContent(idx,1,idx)
            scanInfoHist.SetBinContent(idx,2,int(trim_inv))
            scanInfoHist.SetBinContent(idx,3,len(flist))
    
        # prepare RDF
        rdf = ROOT.RDF.Experimental.FromSpec(task_spec)
        ROOT.RDF.Experimental.AddProgressBar(rdf)
        ix_filter_cond='ix>=0' if ix_filt==-1 else f'ix=={ix_filt}'
        rdf = rdf.DefinePerSample('ix', 'rdfsampleinfo_.GetI("index")') \
             .Filter(ix_filter_cond) \
             .DefinePerSample('target_module_fed', 'rdfsampleinfo_.GetI("fed")') \
             .DefinePerSample('target_module_seq', 'rdfsampleinfo_.GetI("seq")') \
             .Define('target_module', 'HGCDigi_fedId==target_module_fed && HGCDigi_fedReadoutSeq==target_module_seq') \
             .Define('good_digiadc',  'HGCDigi_flags!=0xFFFF && HGCDigi_tctp<3') \
             .Define('maskadc',       'good_digiadc & target_module') \
             .Define('chadc',         'HGCDigi_channel[maskadc]') \
             .Define('chtypeadc',     'HGCDigi_chType[maskadc]') \
             .Define('adc',           'HGCDigi_adc[maskadc]') \
             .Define('modulecm',      'HGCDigi_cm[maskadc]/2') \
             .Filter('Sum(maskadc)>0')

        #add the profile
        chbins = (nch,-0.5,nch-0.5)
        graphlist = [
          rdf.Profile2D(("adcprofile", f"{module};Scan point;Channel;<ADC>", *ptbins, *chbins), 'ix', 'chadc', 'adc'),
          rdf.Profile2D(("modulecmprofile", f"{module};Scan point;Channel;<ADC>", *ptbins, *chbins), 'ix', 'chadc', 'modulecm'),
          rdf.Profile1D(("chType", f"{module};Channel;Channel Type", *chbins), 'chadc', 'chtypeadc')
        ]
        ROOT.RDF.RunGraphs(graphlist)
        histolist = [scanInfoHist]
        histolist += [obj.GetValue() for obj in graphlist]
        postfix='' if ix_filt==-1 else f'_ix{ix_filt}'
        rfile = f'{outdir}/{module}{postfix}.root'
        fillHistogramsAndSave(histolist = histolist, rfile = rfile)
        return (module,rfile)

    @staticmethod
    def analyze(args):
        """
        profiles the Channel vs ADC vs CM histogram to find pedestals to use the fit results are stored visually in a PDF file
        """

        typecode, url, cmdargs = args

        #prepare for plotting if required
        doPlots = False if cmdargs.disableControlPlots else True
        if doPlots:
          plt.style.use(hep.style.CMS)
          pdf_url = url.replace('.root','_fits.pdf')
          pdf = PdfPages(pdf_url)
        
        #model for <adc> vs <trim_inv> in each channel
        trim_inv_model = lambda x,a,b : a*x+b
        
        #loop over channels and fit
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
            #fit the model
            try:
              popt, pcov = curve_fit(trim_inv_model, x, y, sigma=yerr)
              popt_unc = np.sqrt(np.diag(pcov))
              yexp=trim_inv_model(x,*popt)
              chi2 = (((y-yexp)/yerr)**2).sum()
              ndof = len(x)-len(popt)
              fit_results.append( [ierx, ich+choffset, popt[0], popt_unc[0], popt[1], popt_unc[1], chi2/ndof, True, chType] )
            except Exception as e:
              print(e)
              fit_results.append( [ierx, ich+choffset] + [-1]*5 + [False]+ [chType] )

            #show the fit result
            if not doPlots: continue
            #ix = ich%ax.shape[0]
            #iy = int(ich/ax.shape[0])
            if ich == -1: ix, iy = ax.shape[0] - 1, ax.shape[1] - 1
            else:
             ix = ich % ax.shape[0]
             iy = int(ich / ax.shape[0])

            ax[ix,iy].grid()
            ax[ix,iy].errorbar(x,y,yerr=yerr,marker='o',elinewidth=1,capsize=1,color='k',ls='none')

            txtargs = { 'transform':ax[ix,iy].transAxes, 'fontsize':12 }
            if fit_results[-1][-2]:
              ax[ix,iy].plot(x,yexp,ls='-')
              channel_name = "CM channel" if ich == -1 else f'Channel {ich+choffset}'
              ax[ix, iy].text(0.1, 0.9, channel_name, **txtargs)
              #ax[ix,iy].text(0.1,0.9,f'Channel {ich+choffset}', **txtargs)
              ax[ix,iy].text(0.1,0.85,rf'Slope= ${popt[0]:3.2f} \pm {popt_unc[0]:3.2f}$', **txtargs)
              ax[ix,iy].text(0.1,0.8,rf'Offset = ${popt[1]:3.2f} \pm {popt_unc[1]:3.2f}$', **txtargs)
              ax[ix,iy].text(0.1,0.75,rf'$\chi^2/dof={chi2:3.2f}/{ndof}$', **txtargs)
            else:
              ax[ix,iy].text(0.1,0.9,f'Channel {ich+choffset} fit failed', **txtargs, bbox={'facecolor':'red', 'alpha':0.5})

          #finalize page
          if not doPlots: continue
          plt.subplots_adjust(wspace=0, hspace=0)
          pdf.attach_note(f'Fits to channels in e-Rx {ierx+1}')
          pdf.savefig()
          plt.close()

        #convert to a pandas for further manipulation
        fit_results = pd.DataFrame(
          fit_results,
          columns = ['ierx','ich','slope','slope_unc','offset','offset_unc','reduced_chi2','valid','chType']
        )

        #determine the max offset per erx
        #start by determining the median and the standard deviation (s.d.)
        #determine max offset from fit which are within 2-s.d. of the median
        mask_valid = (fit_results['valid']==True)
        criteria = fit_results[mask_valid].groupby('ierx')['offset'].agg(['median','std']).to_dict()
        median_offset = fit_results['ierx'].map(criteria['median'])
        std_offset = fit_results['ierx'].map(criteria['std'])
        fit_matches_criteria = (np.abs(fit_results['offset']-median_offset)<2*std_offset)        
        maxoffset_per_erx = fit_results[mask_valid & fit_matches_criteria].groupby('ierx')['offset'].agg('max').to_dict()
        fit_results['max_offset'] = fit_results['ierx'].map(maxoffset_per_erx)

        #determine the best trim_inv per channel (clip to 6b DAC = [0,64[ and round to integer)
        fit_results['trim_inv_optim'] = np.rint( np.clip(
          (fit_results['max_offset']-fit_results['offset'])/fit_results['slope'],
          0, 64
        ) )
                
        #do some histogramming as summary
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
        
        #all done here
        return {'Typecode':typecode,'Fits':fit_results}

      
    def createCorrectionsFile(self, results):

        """ final tweaks of the analysis results to export as yaml """
        
        data = {'calib': {}, 'ch': {}, 'cm': {}}
        for entry in results:
            typecode, fits = entry['Typecode'], entry['Fits']
            fits = fits.set_index(['ich']).sort_index()
            fits['roc'] = fits['ierx'].floordiv(2)
            fits['trim_inv'] = fits['trim_inv_optim'].fillna(0).astype('int').clip(upper=63)
            fits = fits[['roc', 'trim_inv', 'chType']]
            masks = {'calib': fits['chType'] == 0, 'ch': (fits['chType'] == -1) | (fits['chType'] == 1), 'cm': fits['chType'] == 2}
            for key, mask in masks.items():
                data[key][typecode] = fits[mask].groupby('roc').apply(
                    lambda roc: (r := roc.reset_index(drop = True)).groupby(r.index).apply(
                        lambda ch : ch[["trim_inv"]].to_dict("records")[0]
                    ).to_dict()
                ).to_dict()

        yamlurl = []
        for typecode, rocs in data['ch'].items():
            for roc in rocs.keys():
                yamlurl.append(f'{self.cmdargs.output}/{typecode.replace("_", "-")}_roc{roc}.yaml')
                output = {k: data[k][typecode][roc] if roc in data[k][typecode] else {} for k in data.keys()}
                with open(yamlurl[-1], 'w') as yaml_file:
                    yaml.dump(output, yaml_file, default_flow_style=False)

        return yamlurl

      

if __name__ == '__main__':
  HGCALTrimInvScan()
