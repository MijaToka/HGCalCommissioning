# Author: Izaak Neutelings (November 2024)
# Instructions:
#   python3 scripts/HGCalTrigTimeAnalysis.py -r 1727204018 -i /eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/SepTB2024/
#   python3 scripts/HGCalTrigTimeAnalysis.py -r 1727204018 -i /eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/SepTB2024/ --skipHistoFiller
#   for r in 1727206292 1727204018; do for k in 3 4 5; do python3 scripts/HGCalTrigTimeAnalysis.py -r $r -i /eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/SepTB2024/ --skipHistoFiller --krms $k; done; done
import os, sys
sys.path.append("./")
import re
from HGCalMIPScaleAnalysis import HGCalMIPScaleAnalysis
from plotTrigTime import makeTrigTimeWindow
from HGCalCommissioning.LocalCalibration.plot.wafer import fill_wafer_hist
from HGCalCommissioning.LocalCalibration.plot.utils import setstyle, makehist, makegraph, copytdir, makeHistComparisonCanvas
import math
import numpy as np
from scipy import stats
import itertools
import ROOT


def profile(h_Emean, h_Eprof, h_Emax=None):
    """Help function to profile mean energy vs. trigtime."""
    ny = h_Emean.GetXaxis().GetNbins()
    nz = h_Emean.GetYaxis().GetNbins()
    for ybin in range(1,ny+1): # loop over y=trigphase
        Emax = -1
        Etot, ntot = 0, 0
        for zbin in reversed(range(1,nz+1)): # loop over z=energy from top
            z = h_Emean.GetYaxis().GetBinCenter(zbin) # energy
            nhits = h_Emean.GetBinContent(ybin,zbin)
            ntot += nhits # number of hits
            Etot += nhits*z # energy weighted by number of hits
            if Emax<0 and nhits>0: # first nonzero bin for this y=trigphase value
                Emax = z
        if ntot>0:
            profz = Etot/ntot # profile (Emean averaged over channels)
            h_Eprof.SetBinContent(ybin,profz)
        if Emax>0 and (h_Emax is not None):
            h_Emax.SetBinContent(ybin,Emax)
    

def findTrigPhaseWindow(tpvals, zmeans, maxDrop, xbin, h_Emax=None, h_Eprof=None, h_error=None):
    """Help function to find trigphase window."""
    tpvals, zmeans = tpvals[2:], zmeans[2:] # exclude (exclude tp<1)
    zmean_max = zmeans.max() # maximum zmeans in this channel 
    if zmean_max<=0:
        if h_error:
            h_error.SetBinContent(xbin,3) # 3 = no max mean
        return None
    try:
        zcut = maxDrop*zmean_max
        #accept = np.argwhere(zmeans > zcut).ravel().tolist()
        accept = tpvals[zmeans>zcut]
        tpmin, tpmax = accept.min(), accept.max()
        tpmids = tpvals[zmeans==zmean_max]
        tpmid  = tpmids[tpmids.size//2] # trigphase with maximum mean
        #print(f">>> channel={xbin}: trigtime ({tpmin:4.2g},{tpmax:4.2g})"
        #      f" with max_mean={zmean_max:4.2g} at {tpmid:4.2g}, zcut={zcut:4.2g}")
    except ValueError as err:
        print("findTrigPhaseWindow: Got ValueError: zmeans={zmeans}, zcut={zcut}, accept={accept}")
        raise err
    if h_Emax:
        h_Emax.SetBinContent(xbin,zmean_max)
    if h_Eprof:
        profz = zmeans.mean() # profile (Emean averaged over trigphase)
        h_Eprof.SetBinContent(xbin,profz) # averaged over trigphase
    if tpmin>=tpmax and h_error:
        h_error.SetBinContent(xbin,4) # 4 = no valid window
    return (tpmin,tpmax,tpmid)
    

def addTrigPhaseWindow(xbin, x, tpwindow, h_tpmin, h_tpmax, g_tpmid, width=1):
    """Help function to add trigphase window to histograms & graph."""
    tpmin, tpmax, tpmid = tpwindow
    h_tpmin.SetBinContent(xbin,tpmin)
    h_tpmin.SetBinError(xbin,1e-9) # for plotting
    h_tpmax.SetBinContent(xbin,tpmax)
    h_tpmax.SetBinError(xbin,1e-9) # for plotting
    g_tpmid.SetPoint(xbin-1,x,tpmid)
    g_tpmid.SetPointError(xbin-1,width/2.,width/2.,max(1e-9,tpmid-tpmin),max(1e-9,tpmax-tpmid))
    

def getmean(num,den):
    """Help function to compute mean num/den=Etot/nhits, taking care of zero denominator."""
    mask = (den!=0) # mask to prevent division by zero
    means = np.zeros(num.size) # mean energy vs. triggerphase for this ROC
    means[mask] = num[mask]/den[mask]
    return means

def insertlist(oldlist,newlist,element):
    """Help function to insert list behind a given element."""
    iold = oldlist.index(element)+1
    oldlist = oldlist[:iold]+newlist+oldlist[iold:] # insert newlist
    return oldlist
    
    

class HGCalTrigTimeAnalysis(HGCalMIPScaleAnalysis):
    """
    Study of trig phase to optimize window for MIP scale analysis.
    """
    
    def __init__(self):
        self.histofiller = self.mipHistoFiller
        self.createCorrectionsFile = self.mergeROOTFiles
        #ROOT.gROOT.SetBatch(True)
        #ROOT.gInterpreter.Declare('#include "interface/fit_models.h"')
        #ROOT.shushRooFit()
        super().__init__()

    def addCommandLineOptions(self, parser):
        """add specific command line options for pedestals"""
        super().addCommandLineOptions(parser)
        #parser.add_argument("--plot", action='store_true',
        #                    help='plot results')
        #parser.add_argument("--mergeOnly",
        #                    action='store_true',
        #                    help='only merge output ROOT files')
        parser.add_argument("--postfix",type=str,default="_krms$RKMS",
                            help='postfix for output files, default=%(default)')
        parser.add_argument("--krms",type=float,default=4,
                            help='number of RMS to define E_min threshold, default=%(default)')
    
    def mergeROOTFiles(self, results):        
        """Merge ROOT files for convenience."""
        if not results:
          print("mergeROOTFiles: Did not any results...")
          return None
        postfix = self.getpostfix(self.cmdargs)
        outdir  = os.path.dirname(results[0])
        rooturl = os.path.join(outdir,f"trigstudy{postfix}.root")
        outfile = ROOT.TFile.Open(rooturl,'RECREATE')
        fname_exp = re.compile(f"(?:.*/)?trigstudy_([^/]+).root")
        for fname in sorted(results):
          match = fname_exp.match(fname)
          if not match:
            print(f">>> Did not recognize {fname!r} in {fname_exp.pattern!r} pattern! Skipping...")
            continue
          typecode = match.group(1) # module typecode
          subdir = outfile.mkdir(typecode)
          #print(f">>> Copying contents from {fname!r} to {subdir.GetPath()!r}...")
          copytdir(fname,subdir)
        outfile.Close()
        return rooturl
    
    @staticmethod
    def getpostfix(cmdargs):
        strkrms = str(cmdargs.krms).rstrip('0').rstrip('.') # remove trailing 0
        postfix = cmdargs.postfix
        postfix = cmdargs.postfix.replace('$RKMS',strkrms)
        return postfix
    
    @staticmethod
    def analyze(args):
        """analyzes a 3D histogram of channel vs trig time vs observable
        for each channel determines the RMS from the inclusive distribution of the observable
        a threshold is then defined loc + krms*RMS
        the algorithm then profiles the observable (for observable > threshold) 
        as function of trigtime and finds it's maximum
        the proposed trig time range (by which it drops at most by maxDrop) is returned per channel
        """
        typecode, url, cmdargs = args
        krms = cmdargs.krms # defines E_min threshold as number or pedestal noise (RMS)
        maxDrop = 0.90 # defines lower cut for trigtime
        
        # open the ROOT file and read the histograms of interest
        infile = ROOT.TFile.Open(url,'READ')
        hist3d = infile.Get('en') # energy vs. trigphase vs. channel
        outhists = [ hist3d ] # histograms to write
        outgraphs = [ ] # graphs to write
        outhists_ch = { } # channel-level histograms to write
        
        # get general info
        xtitle = hist3d.GetXaxis().GetTitle() # channel
        ytitle = hist3d.GetYaxis().GetTitle() # trigphase
        ztitle = hist3d.GetZaxis().GetTitle() # RecHit energy (after pedestal & CM subtraction)
        nx, xmin, xmax = hist3d.GetNbinsX(), hist3d.GetXaxis().GetXmin(), hist3d.GetXaxis().GetXmax()
        ny, ymin, ymax = hist3d.GetNbinsY(), hist3d.GetYaxis().GetXmin(), hist3d.GetYaxis().GetXmax()
        nz, zmin, zmax = hist3d.GetNbinsZ(), hist3d.GetZaxis().GetXmin(), hist3d.GetZaxis().GetXmax()
        
        # maximum trigphase
        h_tp = hist3d.Project3D('y') # project all channels & energy
        h_tp.SetName('tp')
        h_tp.SetTitle("Trigger phase (all channels & energy)")
        ny_max = ny
        for ybin in reversed(range(1,ny+1)): # loop over y=trigphase
            nevts = h_tp.GetBinContent(ybin)
            if nevts==0: # empty bin
                ny_max = ybin
            else:
                break
        if ny_max<nx:
            ny_max += 2 # for some margin
        #print(f">>> Module {typecode}: ny_max={ny_max}")
        
        # project 3D onto 2D along x=channels or y=trigphase axis
        # https://root.cern.ch/doc/master/classTH3.html#a65ed465ab42638e18ba9ee50b14fa4ad
        h_E_vs_ch = hist3d.Project3D('zx') # project all y=trigphase
        h_E_vs_tp = hist3d.Project3D('zy') # project all x=channels
        h_E_vs_ch.SetName('E_vs_channel')
        h_E_vs_tp.SetName('E_vs_trigphase')
        h_E_vs_ch.SetTitle("Energy vs. channel (all trigphase)")
        h_E_vs_tp.SetTitle("Energy vs. trigphase (all channels)")
        h_E_vs_ch_Ecut     = ROOT.TH2F('E_vs_channel_Ecut',   f"Energy vs. channel (all trigphase, E > E_{{min}});{xtitle};{ztitle}", nx,xmin,xmax,nz,zmin,zmax)
        h_E_vs_tp_Ecut     = ROOT.TH2F('E_vs_trigphase_Ecut', f"Energy vs. trigphase (all channels, E > E_{{min}});{ytitle};{ztitle}",ny,ymin,ymax,nz,zmin,zmax)
        h_E_vs_ch_tpcut    = ROOT.TH2F('E_vs_channel_tpcut',  f"Energy vs. channel (all trigphase, E > E_{{min}}, window);{xtitle};{ztitle}", nx,xmin,xmax,nz,zmin,zmax)
        h_E_vs_tp_tpcut    = ROOT.TH2F('E_vs_trigphase_tpcut',f"Energy vs. trigphase (all channels, E > E_{{min}}, window);{ytitle};{ztitle}",ny,ymin,ymax,nz,zmin,zmax)
        h_Etot_vs_ch_Ecut  = makehist('Etot_vs_channel_Ecut', f"Integrated energy (E > E_{{min}});{xtitle};Integrated energy",nx,xmin,xmax)
        h_Etot_vs_ch_tpcut = makehist('Etot_vs_channel_tpcut',f"Integrated energy (E > E_{{min}}, window);{xtitle};Integrated energy",nx,xmin,xmax)
        h_error_vs_ch      = makehist('err_vs_channel',       f"Error: 1/2=empty, 3=no mean, 4=no window;{xtitle};Error code",nx,xmin,xmax) #,ymin=0,ymax=2)
        outhists += [ # histograms to write
          h_E_vs_ch, h_E_vs_ch_Ecut, h_E_vs_ch_tpcut,
          h_error_vs_ch,
          h_Etot_vs_ch_Ecut, h_Etot_vs_ch_tpcut,
          h_E_vs_tp, h_E_vs_tp_Ecut, h_E_vs_tp_tpcut,
        ]
        
        # prepare other 1D & 2D histograms
        strkrms = str(krms).rstrip('0').rstrip('.')
        etitle = f"Threshold E_{{min}} = <E> + {strkrms}*RMS"
        h_loc_vs_ch    = makehist( 'loc_vs_channel',    f"Mean energy vs. channel;{xtitle};Mean Energy",nx,xmin,xmax,ymin=-2,ymax=5)
        h_rms_vs_ch    = makehist( 'rms_vs_channel',    f"Energy RMS vs. trigphase;{xtitle};Energy RMS",nx,xmin,xmax,ymin=-2,ymax=5)
        h_Emin_vs_ch   = makehist( 'Emin_vs_channel',   f"Threshold above noise (E > E_{{min}}, krms={strkrms});{xtitle};{etitle}",nx,xmin,xmax,ymin=0,ymax=zmax)
        h_Emin_vs_tp   = ROOT.TH2F('Emin_vs_trigphase', f"Threshold above noise (E > E_{{min}}, krms={strkrms});{ytitle};{etitle}",ny,ymin,ymax,nz,zmin,zmax)
        h_Emean_vs_ch  = ROOT.TH2F('Emean_vs_channel',  f"Mean energy vs. channel (E > E_{{min}});{xtitle};Mean energy",  nx,xmin,xmax,nz,zmin,zmax)
        h_Emean_vs_tp  = ROOT.TH2F('Emean_vs_trigphase',f"Mean energy vs. trigphase (E > E_{{min}});{ytitle};Mean energy",ny,ymin,ymax,nz,zmin,zmax)
        h_Eprof_vs_ch  = makehist( 'Eprof_vs_channel',  f"Mean energy profile vs. channel (E > E_{{min}});{xtitle};Mean energy profile",  nx,xmin,xmax,ymin=0,ymax=zmax)
        h_Eprof_vs_tp  = makehist( 'Eprof_vs_trigphase',f"Mean energy profile vs. trigphase (E > E_{{min}});{ytitle};Mean energy profile",ny,ymin,ymax,ymin=0,ymax=zmax)
        h_Emax_vs_ch   = makehist( 'Emax_vs_channel',   f"Maximum mean energy vs. channel (E > E_{{min}});{xtitle};Maximum mean energy",  nx,xmin,xmax,ymin=0,ymax=zmax)
        h_Emax_vs_tp   = makehist( 'Emax_vs_trigphase', f"Maximum mean energy vs. trigphase (E > E_{{min}});{ytitle};Maximum mean energy",ny,ymin,ymax,ymin=0,ymax=zmax)
        h_tpmin_vs_ch  = makehist( 'tpmin_vs_channel',  f"Trig phase window minimum vs. channel (krms={strkrms}, drop={maxDrop});{xtitle};{ytitle} window minimum",nx,xmin,xmax,ymin=30,ymax=85)
        h_tpmax_vs_ch  = makehist( 'tpmax_vs_channel',  f"Trig phase window maximum vs. channel (krms={strkrms}, drop={maxDrop});{xtitle};{ytitle} window maximum",nx,xmin,xmax,ymin=30,ymax=85)
        g_tpmid_vs_ch  = makegraph('tpmid_vs_channel',  f"Trig phase of maximum <E> vs. channel (krms={strkrms}, drop={maxDrop});{xtitle};{ytitle} of maximum <E>",nx,ymin=30,ymax=85,errors=True)
        outhists += [
            h_loc_vs_ch,   h_rms_vs_ch,
            h_Emin_vs_ch,  h_Emin_vs_tp,
            h_Emean_vs_ch, h_Eprof_vs_ch,
            h_Emean_vs_tp, h_Eprof_vs_tp,
            h_Emax_vs_ch,  h_Emax_vs_tp,
            h_tpmin_vs_ch, h_tpmax_vs_ch, g_tpmid_vs_ch
        ]
        
        # settings for eRx/ROCs
        nchans = { }
        nchans['erx'] = 37 # 37 per half-ROC (eRx)
        nchans['roc'] = 2*nchans['erx'] # 74 per half-ROC (eRx)
        if nx%nchans['roc']!=0:
            print(f">>> Warning! nx%nchans['roc'] = {nx}%{nchans['roc']} !=0 for module {typecode}!")
        
        # prepare histograms for each eRx/ROC
        modhists = { k: { } for k in ['Emean','Eprof','Emax','tpmin','tpmax','tpmid'] }
        Etot_vs_tp, nhits_vs_tp = { }, { } # arrays to compute means
        for modkey, modtitle in reversed([('erx',"eRx"),('roc',"ROC")]):
            
            # prepare histograms vs. triggerphase
            nmods = int(math.ceil(float(nx)/nchans[modkey])) # number of eRx/ROC bins
            for histkey, hold in [('Emean',h_Emean_vs_tp),('Eprof',h_Eprof_vs_tp),('Emax',h_Emax_vs_tp)]:
                modhists[histkey][modkey] = [ ]
                for imod in range(nmods):
                    hnew = hold.Clone(hold.GetName()+f"_{modkey}{imod}")
                    hnew.SetTitle(hold.GetTitle().replace(" (",f", {modtitle} {imod} ("))
                    hnew.GetYaxis().SetRangeUser(0,zmax) # for plotting
                    modhists[histkey][modkey].append(hnew)
                outhists = insertlist(outhists,modhists[histkey][modkey],hold)
            
            # prepare histogram vs. channel
            info = f"{modtitle} (krms={strkrms}, drop={maxDrop});{xtitle};{ytitle}"
            modhists['tpmin'][modkey] = makehist( f'tpmin_vs_{modkey}',f"Trig phase window minimum vs. {info} window minimum",nmods,xmin,xmax,ymin=40,ymax=90)
            modhists['tpmax'][modkey] = makehist( f'tpmax_vs_{modkey}',f"Trig phase window maximum vs. {info} window maximum",nmods,xmin,xmax,ymin=40,ymax=90)
            modhists['tpmid'][modkey] = makegraph(f'tpmid_vs_{modkey}',f"Trig phase of maximum <E> vs. {info} of maximum <E>",nmods,ymin=40,ymax=90,errors=True)
            Etot_vs_tp[modkey]  = np.zeros(ny)
            nhits_vs_tp[modkey] = np.zeros(ny)
            newlists = [ modhists['tpmin'][modkey], modhists['tpmax'][modkey], modhists['tpmid'][modkey] ]
            outhists = insertlist(outhists,newlists,g_tpmid_vs_ch)
        
        # set default style for viewing in browser
        for hist in [h_Emin_vs_tp,h_Emean_vs_ch,h_Emean_vs_tp]:
            hist.GetYaxis().SetRangeUser(0,zmax) # for plotting
        for hist in outhists:
            if isinstance(hist,ROOT.TH1F):
                setstyle(hist)
        
        # y=triggerphase axis
        yaxis  = hist3d.GetYaxis()
        tpvals = np.array([yaxis.GetBinCenter(i) for i in range(1,ny+1)])
        
        # max energy to compute unbiased noise threshold
        loc_all = hist3d.GetMean(3) # mean energy for the whole module
        rms_all = hist3d.GetRMS(3)
        Emax    = max(7.5,loc_all+4.2*rms_all)
        zbinmax = hist3d.GetZaxis().FindBin(Emax)
        
        # profile energy vs. trigphase per channel
        coi_trigtime = { } # final return value
        hyz = ROOT.TH2F('pyz','',ny,ymin,ymax,nz,zmin,zmax)
        print(f">>> Module {typecode}: ped={loc_all:+6.3f}, rms={rms_all:4.2f} => Emax={Emax:4.2f}")
        for xbin in range(1,nx+1): # loop over x=channels
            x = int(hist3d.GetXaxis().GetBinCenter(xbin)) # channel index
            ierx = x//nchans['erx'] # eRx index (37)
            iroc = x//nchans['roc'] # ROC index (2*37)
            #nexterx = (x+1)//nchans['erx']
            #nextroc = (x+1)//nchans['roc']
            
            # make yz slice for channel x
            hyz.Reset('ICE')
            for ybin, zbin in itertools.product(range(1,ny+1),range(1,nz+1)):
                nevts = hist3d.GetBinContent(xbin,ybin,zbin)
                hyz.SetBinContent(ybin,zbin,nevts)
            
            # determine a noise threshold from the inclusive distribution of the observable
            hyz.GetYaxis().SetRange(1,zbinmax) # apply E<Emax limit to unbias the mean/rms computation
            #print(f">>> Emax={Emax:5.2f} in bin={zbinmax:2d}: loc={loc_all:6.4f} -> {hyz.GetMean(2):7.4f}, rms={rms_all:5.2f} -> {hyz.GetRMS(2):6.2f}")
            loc  = hyz.GetMean(2)
            rms  = hyz.GetRMS(2)
            Emin = loc+krms*rms # theshold above noise
            hyz.GetYaxis().SetRange(0,0) # reset range
            h_loc_vs_ch.SetBinContent(xbin,loc)
            h_loc_vs_ch.SetBinError(xbin,rms)
            h_rms_vs_ch.SetBinContent(xbin,rms)
            h_Emin_vs_ch.SetBinContent(xbin,Emin) # theshold above noise
            if rms<1e-6: # set defaults & skip
                h_error_vs_ch.SetBinContent(xbin,1) # 1=empty
                g_tpmid_vs_ch.SetPoint(xbin-1,x,0)
                continue
            
            # bin to start integrating from
            zbinmin = hist3d.GetZaxis().FindBin(Emin)+1
            
            # if bin not valid, set mean to 0 and skip
            Emean_vs_tp = np.zeros(ny) # array with default zeroes
            isempty = (zbinmin<=1 or zbinmin>nz)
            if isempty:
                h_error_vs_ch.SetBinContent(xbin,2) # 2=empty
            
            # profile the observable in trigtime for values above the noise (E > Emin)
            else:
                for ybin in range(2,ny_max+1): # loop over y=trigphase (exclude tp<1, bin 1)
                    y = yaxis.GetBinCenter(ybin) # trigphase
                    nhits, Etot = 0., 0.
                    for zbin in range(zbinmin,nz+1): # loop over z=energy
                        z = hyz.GetYaxis().GetBinCenter(zbin)
                        w = hyz.GetBinContent(ybin,zbin)
                        nhits += w # number of hits
                        Etot  += z*w # energy weighted by number of hits
                        h_E_vs_ch_Ecut.Fill(x,z,w) # count hits with energy above threshold
                        h_E_vs_tp_Ecut.Fill(y,z,w) # count hits with energy above threshold
                        h_Etot_vs_ch_Ecut.Fill(x,z*w) # integrate energy above threshold
                    if nhits>0:
                        Emean = Etot/nhits # mean energy for this channel & trigphase
                        h_Emin_vs_tp.Fill(y,Emin)
                        h_Emean_vs_ch.Fill(x,Emean)
                        h_Emean_vs_tp.Fill(y,Emean)
                        modhists['Emean']['erx'][ierx].Fill(y,Emean)
                        modhists['Emean']['roc'][iroc].Fill(y,Emean)
                        Emean_vs_tp[ybin-1] = Emean
                        for key in Etot_vs_tp:
                            Etot_vs_tp[key][ybin-1] += Etot
                            nhits_vs_tp[key][ybin-1] += nhits
                
                hyz.GetYaxis().SetRange(0,0) # reset range
            
            # determine the acceptable trigtime window
            tpmin, tpmax = 0, 0
            tpwindow = findTrigPhaseWindow(tpvals,Emean_vs_tp,maxDrop,xbin,h_Emax_vs_ch,h_Eprof_vs_ch,h_error_vs_ch)
            if tpwindow:
                tpmin, tpmax, tpmid = tpwindow
                coi_trigtime[xbin] = tpwindow
                addTrigPhaseWindow(xbin,x,tpwindow,h_tpmin_vs_ch,h_tpmax_vs_ch,g_tpmid_vs_ch)
            hasValidWindow = (tpmin<tpmax)
            
            # determine the acceptable trigtime window if this is the last channel of the eRx/ROC
            for key in modhists['tpmin']: # loop over key = 'erx', 'mod'
                imod, inext = x//nchans[key], (x+1)//nchans[key]
                if imod!=inext: # last channel of this eRx/ROC
                    xmod = (imod+0.5)*nchans[key] # middle channel for graph
                    modbin = modhists['tpmin'][key].GetXaxis().FindBin(xmod)
                    Emean_vs_tp = getmean(Etot_vs_tp[key],nhits_vs_tp[key])
                    tpwindow = findTrigPhaseWindow(tpvals,Emean_vs_tp,maxDrop,modbin)
                    if tpwindow:
                        addTrigPhaseWindow(modbin,xmod,tpwindow,modhists['tpmin'][key],modhists['tpmax'][key],modhists['tpmid'][key],nchans[key])
                    Etot_vs_tp[key][:] = 0 # reset for next eRx
                    nhits_vs_tp[key][:] = 0
            
            # profile again, but with trigger window cuts (E > Emin, in trigphase window)
            if not isempty and hasValidWindow:
                ybin_min, ybin_max = yaxis.FindBin(tpmin), yaxis.FindBin(tpmax)
                for ybin in range(ybin_min,ybin_max+1): # loop loop over y=trigphase
                    y = yaxis.GetBinCenter(ybin) # trigphase
                    for zbin in range(zbinmin,nz+1): # loop over z=energy
                        z     = hyz.GetYaxis().GetBinCenter(zbin) # energy
                        nhits = hyz.GetBinContent(ybin,zbin)
                        Etot  = z*nhits
                        h_E_vs_ch_tpcut.Fill(x,z,nhits) # count hits with energy above threshold
                        h_E_vs_tp_tpcut.Fill(y,z,nhits) # count hits with energy above threshold
                        h_Etot_vs_ch_tpcut.Fill(x,Etot) # integrate energy above threshold
            
            #### store slice for this channel
            ###htitle = "Energy vs. trigphase (all channels)"
            ###E_vs_tp_ch = hyz.Clone(f"E_vs_trigphase_ch{x:03d}")
            ###E_vs_tp_ch.SetTitle(f"{htitle};{ytitle};{ztitle})
            ###outhists_ch[x] = [ E_vs_tp_ch ]
            ###if not isempty:
            ###    E_vs_tp_ch_Ecut = E_vs_tp_ch.Clone(f"E_vs_trigphase_ch{x:03d}_Ecut")
            ###    E_vs_tp_ch_Ecut.SetTitle(htitle.replace(')',"E > E_{min})"))
            ###    outhists_ch[x].append(E_vs_tp_ch_Ecut)
            ###    for zbin in range(0,zbinmin): # loop over z=energy
            ###        for ybin in range(1,ny_max+1): # loop over y=trigphase
            ###            E_vs_tp_ch_Ecut.SetBinContent(ybin,zbin,0.0) # remove
            ###    if hasValidWindow:
            ###        E_vs_tp_ch_tpcut = E_vs_tp_ch_Ecut.Clone(f"E_vs_trigphase_ch{x:03d}_tpcut")
            ###        E_vs_tp_ch_tpcut.SetTitle(htitle.replace(')',"E > E_{min}, window)"))
            ###        outhists_ch[x].append(E_vs_tp_ch_tpcut)
            ###        for zbin in range(zbinmin,nz+1): # loop over z=energy
            ###            for ybin in range(1,ny_max+1): # loop over y=trigphase
            ###                y = yaxis.GetBinCenter(ybin) # trigphase
            ###                if tpmin<y<tpmax:
            ###                    continue
            ###                E_vs_tp_ch_tpcut.SetBinContent(ybin,zbin,0.0) # remove
        
        hyz.Delete()
        
        # get maximum mean energy vs. trigphase
        # by scanning h_Emax_vs_tp from top for each bin of y=trigphase
        profile(h_Emean_vs_tp,h_Eprof_vs_tp,h_Emax_vs_tp)
        for key in modhists['Emean']: # loop over key = 'erx', 'mod'
            nmods = len(modhists['Emean'][key])
            for imod in range(nmods):
                profile(modhists['Emean'][key][imod],modhists['Eprof'][key][imod],modhists['Emax'][key][imod])
        
        # return the mode of the range limits found
        minran = stats.mode( [ran[0] for _, ran in coi_trigtime.items()], nan_policy='raise', keepdims=False)
        maxran = stats.mode( [ran[1] for _, ran in coi_trigtime.items()], nan_policy='raise', keepdims=False)
        moderan = (minran.mode,maxran.mode)
        print(f">>> Automatically recognized window for trigger phase of {typecode!r}: {moderan}")
        
        # create ROOT file
        postfix = HGCalTrigTimeAnalysis.getpostfix(cmdargs)
        rooturl = os.path.join(cmdargs.output,f'trigstudy_{typecode}.root')
        
        # write general histograms
        outfile = ROOT.TFile.Open(rooturl,'RECREATE')
        print(f">>> Writing {len(outhists)} histograms to {rooturl}...")
        for hist in outhists:
            hist.Write()
        
        # write channel-level histograms
        if outhists_ch:
            chdir = outfile.mkdir('channels')
            chdir.cd()
            nhists = sum(len(h) for h in outhists_ch.values())
            print(f">>> Writing {nhists} channel-level histograms to {chdir.GetPath()}...")
            for channel in sorted(outhists_ch.keys()):
                if channel=='all':
                    continue
                for hist in outhists_ch[channel]:
                    hist.Write()
        
        # PLOT
        if cmdargs.doHexPlots:
            plotdir = os.path.join(cmdargs.output,"plots")
            os.makedirs(plotdir,exist_ok=True)
            tdir = outfile.mkdir('plots')
            tdir.cd()
            plots = HGCalTrigTimeAnalysis.plotHex(typecode,outhists,tdir=tdir,outdir=plotdir,postfix=postfix)
        
        # all done
        outfile.Close()
        infile.Close()
        
        return rooturl
    
    @staticmethod
    def plotHex(typecode, hists, tdir=None, outdir=None, postfix=""):        
        """Plot histograms & graphs."""
        ROOT.gStyle.SetOptStat(False)  # don't make stat. box
        ROOT.gStyle.SetOptTitle(False) # don't make title on top of histogram
        
        # plot hexagonal wafer histograms
        mtype = typecode[:4]
        typecode = typecode.replace('_','-')
        mod_exp = re.compile(r"Eprof_vs_trigphase(?:_(roc|erx)(\d*))?$")
        hists_tpwdw = { 'ch': { }, 'erx': { }, 'roc': { } }
        hists_Eprof = { 'erx': { }, 'roc': { } }
        for hist in hists:
            hname = hist.GetName()
            htitle = hist.GetTitle()
            outhist = None
            profmatch = mod_exp.match(hname)
            if isinstance(hist,(ROOT.TH2,ROOT.TH3)):
                continue
            elif profmatch:
                modkey, imod = profmatch.groups()
                if modkey==None:
                    for modkey in hists_Eprof:
                        hists_Eprof[modkey]['All'] = hist
                else:
                    title = f"{modkey.replace('roc','ROC').replace('erx','eRx')} {imod}"
                    hists_Eprof[modkey][title] = hist
            elif '_vs_channel' in hname:
                if isinstance(hist,ROOT.TH1F):
                    nxbins  = hist.GetNbinsX()
                    yvals   = [hist.GetBinContent(i) for i in range(1,nxbins+1)]
                elif isinstance(hist,ROOT.TGraph):
                    npoints = hist.GetN()
                    yvals   = [hist.GetPointY(i) for i in range(npoints)]
                else:
                    continue
                outhist = fill_wafer_hist(yvals,moduletype=mtype)
                outhist.SetName(hname.replace("_vs_channel","_hex"))
                outhist.SetTitle(htitle.replace(" vs. channel",""))
                for prefix in ['tpmin','tpmax','tpmid']:
                    if hname.startswith(prefix):
                        hists_tpwdw['ch'][prefix] = hist
                        outhist.GetZaxis().SetRangeUser(40,90)
                        break
            else:
                for key in ['erx','roc']:
                    if f"_vs_{key}" not in hname: continue
                    for prefix in ['tpmin','tpmax','tpmid']:
                        if hname.startswith(prefix):
                            hists_tpwdw[key][prefix] = hist
                            break
            if outhist and tdir:
                tdir.cd()
                #print(f">>> Writing plot {outhist.GetName()!r}...")
                outhist.Write()
        
        # plot profile comparison
        for modkey, modhists in hists_Eprof.items():
            if len(modhists)<3: continue
            canvas = makeHistComparisonCanvas(modhists,text=typecode,xmin=40,xmax=90,ymin=0,ymax=38,lumi="")
            canvas.SaveAs(f"{outdir}/compare_{modkey}_Eprof-tp_{typecode}{postfix}.png")
            if tdir:
                tdir.cd()
                canvas.SetName(f"Eprof_{modkey}")
                canvas.Write()
            canvas.Close()
        
        # plot trigphase window
        for modkey, modhists in hists_tpwdw.items():
            if len(modhists)<3: continue
            fname  = f"tpwindow_vs_{modkey}"
            canvas = makeTrigTimeWindow(fname,modhists['tpmid'],modhists['tpmin'],modhists['tpmax'])
            canvas.SaveAs(f"{outdir}/{fname}_{typecode}{postfix}.png")
            if tdir:
                tdir.cd()
                canvas.Write()
            canvas.Close()
        
        return


if __name__ == '__main__':
    trigstudy = HGCalTrigTimeAnalysis()
    
