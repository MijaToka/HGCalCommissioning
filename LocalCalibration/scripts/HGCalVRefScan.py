# Author: Izaak Neutelings (April 2025)
# Sources:
#  https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/blob/master/LocalCalibration/scripts/HGCalTrimInvScan.py
#  https://gitlab.cern.ch/hgcal-daq-sw/hexactrl-analysis/-/blob/ROCv3/level0/vrefinv_scan_analysis.py
import os, sys
import re, glob
import ROOT
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages
import mplhep as hep
plt.style.use(hep.style.CMS)
colors = plt.cm.viridis(np.linspace(0,1,37))
markers = ['o', 's', '^', 'D', 'v', 'P', '*', 'X', '<', '>']

# import common HGCalCommissioning tools
import DigiAnalysisUtils as DAU
try:
  from HGCalCommissioning.LocalCalibration.HGCalCalibration import HGCalCalibration
  from HGCalCommissioning.LocalCalibration.JSONEncoder import saveAsJson
except ImportError:
  sys.path.append('./python/')
  from HGCalTrimInvScan import HGCalCalibration
  from JSONEncoder import saveAsJson


class HGCalVRefScan(HGCalCalibration):
    
    def __init__(self, raw_args=None, runtype='Inv_vref', scanparam=None):
        if scanparam is None:
            scanparam = 'Inv_vref' if runtype=='vref_inv_scan' else 'Noinv_vref'
        self.histofiller = DAU.adcScanHistoFiller
        super().__init__(raw_args, runtype=runtype, scanparam=scanparam)
        
    def addCommandLineOptions(self, parser):
        """Add specific command line options for the VRef scan"""
        super().addCommandLineOptions(parser)
        parser.add_argument("--targetadc", type=int, default=300,
                            help="target ADC for VRef optimization, default=%(default)r")
        
    @staticmethod
    def analyze(args):
        """
        Scan the average ADC as a function of Inv_vref or Noinv_vref,
        and find the intercept with target ADC = 300 in the "injected" channel.
        Fit the linear part, and create a PDF file with results.
        """
        # Based on
        # https://gitlab.cern.ch/hgcal-daq-sw/hexactrl-analysis/-/blob/ROCv3/level0/vrefinv_scan_analysis.py
        typecode, url, cmdargs = args
        doPlots = cmdargs.doControlPlots
        
        # get scan info
        fileIn = ROOT.TFile.Open(url)
        scaninfo = fileIn.Get('scaninfo')
        npts = scaninfo.GetNbinsX()
        x = np.array([scaninfo.GetBinContent(ipt+1,2) for ipt in range(npts)])
        
        # get <ADC> data
        adcprofile = fileIn.Get('adcprofile')
        adcprofile.SetErrorOption('s')
        
        # convert FE channel index to channel readout sequence
        chTypeprofile = fileIn.Get('chType') # 0: calibration, 1: channel, 2: common mode
        injChansMap   = fileIn.Get('injChansMap') # 0: calibration, 1: channel, 2: common mode
        nchans = chTypeprofile.GetXaxis().GetNbins() #adcprofile.GetYaxis().GetNbins()
        nerx   = int(nchans/37)
        
        # loop over eRx (half-ROC)
        fitresults = [ ]
        for ierx in range(nerx):
            fitres = [ ]
            
            # loop over channels in eRx
            for ich in range(0,37):     # index in this eRx
                ich_ros = ierx*37 + ich # index of readout sequence in this module: 0-221 for LD, 0-441 for HD
                isInjChan = (injChansMap.GetBinContent(1,ich_ros+1)==1)
                
                # fit if "injected" (HZ_noinv=1)
                if isInjChan:
                    info   = f"{typecode}, ierx={ierx:2}, ich={ich_ros:3}"
                    y      = np.array([adcprofile.GetBinContent(ip+1,ich_ros+1) for ip in range(npts)])
                    ye     = np.array([adcprofile.GetBinError(ip+1,ich_ros+1) for ip in range(npts)])
                    fitres = HGCalVRefScan.fit(x, y, ye, cmdargs.targetadc, info=info, verb=cmdargs.verbosity)
                    fitresults.append([ierx,ich_ros,*fitres])
        
        # convert to a pandas for further manipulation
        optparam  = cmdargs.scanparam #+"_optim"
        df_fitres = pd.DataFrame(
          fitresults,
          columns=['ierx', 'ich', optparam, 'slope', 'slope_unc', 'offset', 'offset_unc', 
                   'reduced_chi2', 'xmin', 'xmax', 'valid']
        )
        #df_fitres.set_index('ierx') # use 'ierx' as index
        
        # replace invalid fits with average value
        if (~df_fitres['valid']).any(): # at least one invalid fit
            if (df_fitres['valid']).any(): # at least one valid fit
                x_ave = int(round(df_fitres[df_fitres['valid']][optparam].mean()))
            else: # all fits are invalid !
                x_ave = 420
                print(f">>> HGCalVRefScan.analyze: Warning! ALL fits were invalid for {typecode}... Using default {xopt_ave} !")
            df_fitres.loc[~df_fitres['valid'],optparam] = x_ave # overwrite
        
        # produce control plots
        if cmdargs.doControlPlots:
            HGCalVRefScan.producePlots(typecode, url, cmdargs, fileIn, df_fitres)
        fileIn.Close() # close to delete profile from memory
        
        # all done here
        return { 'Typecode': typecode, 'Fits': df_fitres }
        
    
    @staticmethod
    def fit(x, y, yerr, target, info="unkown", verb=0):
        """Fit VRef scan data for given channel.
        Find linear regime, fit it, and find intersection with target ADC."""
        
        # find linear regime
        ymin = np.min(y)
        ymax = np.max(y)
        yspan = ymax-ymin
        ids_below = np.where(y<ymin+0.05*yspan)[0] # indices below 5% of min.
        ids_above = np.where(y>ymin+0.95*yspan)[0] # indices above 5% of max.
        ileft, iright = 0, len(y)-1 # default
        if len(ids_above)==0 or len(ids_below)==0:
            print(f">>> HGCalVRefScan.fit: Warning! Could not find linear region for {info}..."
                  f" y={y}, ids_above={ids_above}, ids_below={ids_below}")
        elif ids_below[-1]<ids_above[0]: # rising
            ileft, iright = ids_below[-1], ids_above[0]
        elif ids_above[-1]<ids_below[0]: # descending
            ileft, iright = ids_above[-1], ids_below[0]
        else: # mixed, noisy ?
            print(f">>> HGCalVRefScan.fit: Warning! Could not find linear region for {info}...")
        xfit = x[ileft:iright]
        yfit = y[ileft:iright]
        yerr = np.where(yerr<=0,1e-4,yerr)[ileft:iright] # avoid division by 0
        
        # fit the model
        fitresult = [-1, -1, -1, -1, -1, -1, -1, -1, False] # default
        if len(xfit)>2: # not enough points to accurately fit ?
            try:
                model = lambda x,a,b : a*x+b # linear fit function
                popt, pcov = curve_fit(model, xfit, yfit, sigma=yerr)
                popt_unc = np.sqrt(np.diag(pcov))
                alpha, beta = popt[0], popt[1] # slope, offset
                yexp = model(xfit,alpha,beta)
                chi2 = (((yfit-yexp)/yerr)**2).sum()
                ndof = len(xfit)-len(popt)
                if alpha!=0: # find optimal value as intersection with target y
                    xopt = int(round((target-beta)/alpha))
                    valid = bool(x[0]<=xopt<=x[-1]) # inside scan range
                else:
                    xopt = -1
                    valid = False
                fitresult = [ xopt, alpha, popt_unc[0], beta, popt_unc[1], chi2/ndof,
                              xfit[0], xfit[-1], valid]
            except Exception as e:
                print(e)
        if verb>=1:
            print(f">>> HGCalVRefScan.fit: {info}: xopt={fitresult[0]}, a={fitresult[1]:<5.3g}+-{fitresult[2]:<6.2g}"
                  f", b={fitresult[3]:<4.3g}+-{fitresult[4]:<4.2g}, chi2/ndof={fitresult[5]:<4.3g}, valid={fitresult[8]:1}"
                  f"in lin. region (x,y)[{ileft}]=({xfit[0]},{yfit[0]:.4g}) -> [{iright}]=({xfit[-1]},{yfit[-1]:.4g})")
        return fitresult
        
    
    @staticmethod
    def producePlots(typecode, url, cmdargs, fileIn, df_fitres):
        """Produce control plots."""
        
        # get scan info
        scanparam = cmdargs.scanparam
        targetadc = cmdargs.targetadc
        scaninfo = fileIn.Get('scaninfo')
        npts = scaninfo.GetNbinsX()
        x = np.array([scaninfo.GetBinContent(ipt+1,2) for ipt in range(npts)])
        
        # get <ADC> data
        adcprofile = fileIn.Get('adcprofile')
        adcprofile.SetErrorOption('s')
        nchans = adcprofile.GetNbinsY()
        nerx   = int(nchans/37)
        
        # prepare PDF
        pdf_url = url.replace('.root','_fits.pdf')
        png_url = url.replace('.root','_fits.png')
        pdf = PdfPages(pdf_url)
        nrows = int(np.ceil(nerx/3))
        fig, ax = plt.subplots(nrows, 3, figsize=(22,1.1+5.6*nrows), sharex=True, sharey=True) # 3x2 for LD, 6x2 for HD
        fitgraphs = { } # for summary plots
        
        # loop over eRx (half-ROC)
        x = np.array([scaninfo.GetBinContent(ipt+1,2) for ipt in range(npts)])
        xmin, xmax = np.min(x), np.max(x)
        for ierx in range(nerx):
            
            # prepare plots
            iroc = ierx//2 # HGCROC index
            icol = iroc%3 # plot max. 3 ROC side-by-side
            irow = 2*(ierx//6)+(ierx%2) # 3x2 for LD, 3x4 for HD
            subax = ax[irow][icol] # subplot
            header = f"e-Rx {ierx+1} (ROC {iroc+1})" #f"{typecode.replace('_','-')}, e-Rx {ierx+1}"
            fitres = [ ]
            handles = [ ] # for legend
            ymin, ymax = 0, 0
            
            # loop over channels in eRx
            for ich in range(0,37): # index in this eRx
                ich_rs  = ierx*37 + ich  # index of readout sequence in this module: 0-222 for LD
                ich_erx = ich_rs%37      # index in this HGCROC: 0-74
                label   = f"{ich_erx+1}" # index in this HGCROC, counting from 1
                
                # prepare <ADC> data
                y  = np.array([adcprofile.GetBinContent(ip+1,ich_rs+1) for ip in range(npts)])
                ye = np.array([adcprofile.GetBinError(ip+1,ich_rs+1) for ip in range(npts)])
                ymax = max(ymax,np.max(y))
                
                # plot <ADC> vs. VRef as line and markers with error bars
                isInjChan = ((df_fitres['ierx']==ierx) & (df_fitres['ich']==ich)).any()
                am, al = (0.95,0.3) if isInjChan else (0.6,0.15) # alpha opacity
                subax.plot(x, y, linestyle='-', linewidth=0.8, color=colors[ich], alpha=al)
                subax.errorbar(x, y, yerr=ye, marker=markers[ich%len(markers)], markersize=5.5, linestyle='none',
                               capsize=4, color=colors[ich], markeredgewidth=0, elinewidth=0.8, alpha=am)
                handles.append(Line2D([0], [0], marker=markers[ich%len(markers)], color='none',
                               markerfacecolor=colors[ich], markeredgewidth=0.1, label=label))
            
            # finish eRx subplot
            ymin = max(-40,min(ymin,subax.get_ylim()[0])) # cut off in case of large error bar
            ymax = ymin+1.15*(ymax-ymin) # add 15% margin
            subax.set_ylim(ymin,ymax)
            
            # plot linear fit for this eRx
            fitres = df_fitres[df_fitres['ierx']==ierx].iloc[0]
            alpha  = fitres['slope']
            beta   = fitres['offset']
            y      = np.array([adcprofile.GetBinContent(ip+1,int(fitres['ich'])+1) for ip in range(npts)])
            if alpha!=-1 and beta!=-1: # valid fit
                f_lin  = lambda x: alpha*x+beta # linear function
                x0, x1 = fitres['xmin'], fitres['xmax'] # linear region
                line = (x0,x1), (f_lin(x0),f_lin(x1))
                subax.plot(*line, linestyle='-', linewidth=1, color='red', alpha=1)
                fitgraphs[ierx] = (x,y)
                
                # add arrow of optimal VRef
                if fitres['valid']: # valid fit
                    xopt = fitres[scanparam] # optimal VRef value
                    yopt = f_lin(xopt) # corresponding <ADC> ~ target ADC ~ 300
                    subax.annotate("", xy=(xopt,ymin), xytext=(xopt,yopt),
                                   arrowprops=dict(arrowstyle='->', color='red', linewidth=1.5))
                    subax.text(xopt, yopt, str(xopt), fontsize=20, weight='bold', color='red', ha='left', va='bottom')
            
            # target ADC, legend, labels, ...
            subax.hlines(targetadc, xmin, xmax, linewidth=0.7, colors='red', linestyles=(0,(12,8)))
            leg = subax.legend(handles=handles, fontsize=14, bbox_to_anchor=(0.98,0.98), loc='upper right',
                               ncol=4, handletextpad=0.1, columnspacing=1.0, labelspacing=0.25)
            subax.text(0.96, 0.52, header, fontsize=20, weight='bold',
                       color='black', transform=subax.transAxes, ha='right', va='top')
            if icol==0: # left-most column
                subax.set_ylabel(r"$\langle\mathrm{ADC}\rangle$")
            if irow==(nrows-1) : # bottom row
                subax.set_xlabel(scaninfo.GetYaxis().GetBinLabel(2))
        
        # finish all eRx subplots
        #for subax in ax.flat: # set again to force
        #    subax.set_ylim(ymin, ymax)
        fig.suptitle(f"{typecode.replace('_','-')}", fontsize=35, fontweight='bold', y=0.99)
        #fig.tight_layout(rect=[0,0,1,0.98 if nerx>6 else 0.99],pad=0.2) # automatic margins, [LBRT]
        #plt.subplots_adjust(wspace=0, hspace=0) # separation between bordering plots
        if nerx>6: # HD
            plt.subplots_adjust(left=0.055, right=0.985, top=0.97, bottom=0.04, wspace=0, hspace=0)
        else: # LD / partial
            plt.subplots_adjust(left=0.055, right=0.985, top=0.95, bottom=0.08, wspace=0, hspace=0)
        pdf.attach_note(f"VRef scan for {typecode}")
        fig.savefig(png_url) # write first page as PNG
        pdf.savefig() # write subplots to PDF page
        plt.close() # close subplots
        
        # plot fit results summary
        fig, ax = plt.subplots(3,2,figsize=(16,18))
        nvalid  = df_fitres['valid'].sum() # number of valid fits
        x_erx   = df_fitres['ierx']+1       # eRx index (0–11)
        largs   = dict(marker='o', linestyle='-', color='blue', markeredgewidth=0, markersize=8, linewidth=1, label='Valid')
        eargs   = largs.copy()
        eargs.update(dict(capsize=3, elinewidth=2))
        if nvalid!=0: # plot valid fit results
            e_slp = df_fitres['slope_unc'].clip(lower=0) # slope error
            e_ofs = df_fitres['offset_unc'].clip(lower=0) # offset error
            ax[0][0].plot(    x_erx, df_fitres[scanparam],            **largs) # optimized VRef
            ax[0][1].plot(    x_erx, df_fitres['reduced_chi2'],       **largs) # chi2/dof
            ax[1][0].errorbar(x_erx, df_fitres['slope'],  yerr=e_slp, **eargs) # slope
            ax[1][1].errorbar(x_erx, df_fitres['offset'], yerr=e_ofs, **eargs) # offset
        
        # highlight invalid plots
        df_inv = df_fitres[~df_fitres['valid']] # valid fits
        if len(df_inv)>=1: # plot invalid fits in red
            largs.update(dict(marker='X', linewidth=1.0, markersize=10, linestyle='none', color='red',label='Invalid'))
            dargs = dict(linestyles=(0,(8,5)), linewidth=1.8, color='red', label='Default')
            x_inv = df_inv['ierx']+1
            x_def = [x_erx.iloc[0]-0.2, x_erx.iloc[-1]+0.2] # default
            x_ave = df_inv[scanparam].iloc[0] # default (averaged over e-Rx's)
            ax[0][0].plot(    x_inv, df_inv[scanparam],      **largs) # optimized VRef
            ax[0][1].plot(    x_inv, df_inv['reduced_chi2'], **largs) # chi2/dof
            ax[1][0].errorbar(x_inv, df_inv['slope'],        **largs) # slope
            ax[1][1].errorbar(x_inv, df_inv['offset'],       **largs) # offset
            ax[0][0].hlines(  x_ave, *x_def, **dargs) # default (average)
            ax[0][1].hlines(     -1, *x_def, **dargs) # default
            ax[1][0].hlines(     -1, *x_def, **dargs) # default
            ax[1][1].hlines(     -1, *x_def, **dargs) # default
        
        # plot valid fit graphs
        colors2 = plt.cm.viridis(np.linspace(0,1,len(fitgraphs)))
        if nvalid>=1: # at least on valid fit to plot
            x_ave   = [x for (i,(x,y)) in fitgraphs.items() if df_fitres[df_fitres['ierx']==i]['valid'].iloc[0]][0]
            y_all   = [y for (i,(x,y)) in fitgraphs.items() if df_fitres[df_fitres['ierx']==i]['valid'].iloc[0]]
            y_ave   = np.mean(y_all, axis=0) # average <ADC> over valid fits
            avemask = y_ave!=0
            x_ave   = np.array(x_ave)[avemask]
            y_ave   = y_ave[avemask] # avoid division by 0
        else: # no valid fits to plot
            y_ave   = np.array()
            avemask = np.array()
            ax[2,1].set_axis_off() # do not show this plot
        for i, (ierx, (x,y)) in enumerate(fitgraphs.items()):
             fitres = df_fitres[df_fitres['ierx']==ierx].iloc[0]
             f_lin  = lambda x: fitres['slope']*x + fitres['offset'] # linear function
             largs = dict(marker=markers[i%len(markers)], markersize=5.5, markeredgewidth=0,
                          linestyle='-', linewidth=0.8, capsize=4, elinewidth=0.8,
                          color=colors2[i%len(colors2)], alpha=0.7, label=f"e-Rx {ierx+1}")
             ax[2][0].errorbar(x, y, **largs)
             if len(y_ave)>0 and fitres['valid']:
                 ax[2][1].errorbar(x_ave, y[avemask]/y_ave, **largs)
                 fitmask = (fitres['xmin']<=x_ave) & (x_ave<=fitres['xmax']) # linear region
                 ax[2][1].plot(x_ave[fitmask], f_lin(x_ave[fitmask])/y_ave[fitmask],
                               linestyle='-', linewidth=0.8, color='red')
        
        # plot target line
        for subax in [ax[2][0],ax[2][1]]:
            ymin, ymax = subax.get_ylim()
            subax.set_ylim(ymin,1.07*ymax) # increase white space above for legend
        targs = dict(color='red', linestyle=(0,(8,5)), label="Target") # target line
        ax[2][0].hlines(targetadc, xmin, xmax, **targs)
        if len(y_ave)>0:
            ax[2][1].plot(x_ave, targetadc/y_ave, **targs)
        
        # make up style
        ax[0][0].set_ylabel(f"Optimized {scanparam}")
        ax[0][1].set_ylabel(r"$\chi^2 / dof$")
        ax[1][0].set_ylabel("Slope [ADC counts / VRef]")
        ax[1][1].set_ylabel("Offset [ADC counts]")
        ax[2][0].set_ylabel(r"$\langle\mathrm{ADC}\rangle$")
        ax[2][1].set_ylabel(r"$\langle\mathrm{ADC}\rangle$ / (e-Rx averaged)")
        for subax in [ax[0][0],ax[0][1],ax[1][0],ax[1][1]]: #ax.flat:
            subax.set_xlabel(f"e-Rx index")
            subax.grid()
            subax.legend()
        for subax in [ax[2][0],ax[2][1]]:
            subax.set_xlabel(scanparam)
            subax.grid()
            subax.legend(fontsize=15, ncol=3, columnspacing=2) #, handletextpad=0.1, labelspacing=0.25)
        fig.suptitle(f"{typecode.replace('_','-')} summary", fontsize=30, fontweight='bold', y=0.99)
        fig.tight_layout(rect=[0,0,1,1],pad=0.5) # automatic margins, [LBRT]
        plt.subplots_adjust(wspace=0.2, hspace=0.25)
        
        # write PDF with plots
        pdf.attach_note(f"Summary of fits in VRef scan for {typecode}")
        pdf.savefig() # write subplots to PDF page
        plt.close()
        pdf.close()
        
    
    def createCorrectionsFile(self, results):
        """Final tweaks of the analysis results to export as JSON."""
        jsonurl   = "lol.json"
        corr_dict = { }
        params    = ['ierx',self.scanparam] # parameters to store
        for res in results:
            typecode  = res.pop('Typecode')
            df_fitres = res.pop('Fits')
            sub_dict  = { }
            for param in params:
                parvals = list(df_fitres[param])
                sub_dict[param] = parvals
            corr_dict[typecode] = sub_dict
        jsonurl = f'{self.cmdargs.output}/vrefscan.json'
        saveAsJson(jsonurl, corr_dict)
        return jsonurl
        

if __name__ == '__main__':
    scan = HGCalVRefScan()
  
