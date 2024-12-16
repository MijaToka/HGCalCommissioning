# Author: Izaak Neutelings (November 2024)
# Description:
#   Plot data from HGCalTrigTimeAnalysis.py script & compare modules/relays/configuration.
import os, sys
import glob
sys.path.append("./")
import ROOT
from HGCalCommissioning.LocalCalibration.plot.utils import comparehists, gethist_from_file, setHGCalStyle, addtext
ROOT.gROOT.SetBatch(True)      # don't open GUI windows
ROOT.gStyle.SetOptStat(False)  # don't make stat. box
ROOT.gStyle.SetOptTitle(False) # don't make title on top of histogram


def makeTrigTimeWindow(fname,graph,h_tpmin,h_tpmax,tmarg=0.02,text="",lumi=""):
  """Create canvas with plot of trigger phase window vs. channel or ROC."""
  canvas = ROOT.TCanvas(fname,fname,100,100,1200,800) # XYWH
  canvas.SetMargin(0.10,0.02,0.11,tmarg) # LRBT
  canvas.SetTicks(1,1)
  frame = h_tpmin #canvas.DrawFrame(xmin,ymin,xmax,ymax)
  frame.GetXaxis().SetTitleSize(0.052)
  frame.GetYaxis().SetTitleSize(0.052)
  frame.GetXaxis().SetLabelSize(0.048)
  frame.GetYaxis().SetLabelSize(0.048)
  frame.SetMinimum(44)
  frame.SetMaximum(90)
  frame.SetTitle("")
  frame.Draw('AXIS')
  graph.SetFillColor(ROOT.kAzure-9)
  graph.SetFillStyle(1001)
  graph.SetMarkerColor(ROOT.kMagenta)
  graph.SetMarkerSize(0.5)
  graph.SetLineWidth(0)
  graph.Draw('2SAME') # filled
  graph.Draw('PSAME') # marker
  lcols = [ROOT.kBlue,ROOT.kRed]
  for i, hist in enumerate([h_tpmin,h_tpmax]):
    color = lcols[i%len(lcols)]
    hist.SetLineColor(color)
    hist.SetLineWidth(3)
    hist.SetMarkerColor(color)
    hist.SetMarkerSize(0.1)
    hist.Draw('ESAME')
  if lumi:
    setHGCalStyle(canvas,lumiText=lumi)
  if text:
    latex = addtext(canvas,text,tsize=0.050)
  canvas.RedrawAxis()
  return canvas
  

def plotTrigTimeWindow(path,vstag="_vs_channel",tag="",lumi="",text=None,exts=['.png','.pdf'],outdir='plots'):
  """Plot trigger phase window vs. channel or ROC for MIP fit."""
  cname   = f"tpwindow{vstag}{tag}"
  fname   = os.path.join(outdir,cname)
  g_tpmid = gethist_from_file(path+"tpmid"+vstag)
  h_tpmin = gethist_from_file(path+"tpmin"+vstag)
  h_tpmax = gethist_from_file(path+"tpmax"+vstag)
  canvas  = makeTrigTimeWindow(cname,g_tpmid,h_tpmin,h_tpmax,tmarg=0.05,text=text,lumi=lumi)
  for ext in exts:
    canvas.SaveAs(fname+ext)
  canvas.Close()
  

def main(args):
  
  outdir  = args.outdir
  indir   = args.indir
  modules = args.modules
  relays  = [str(r) for r in args.relays] # ensure string
  lumi    = args.lumitext
  tag     = args.tag
  tmin, tmax = 45, 82
  #fglob  = os.path.join(indir,"Relay17*/trigstudy_krms*.root")
  #fnames = glob.glob(fglob)
  
#   # COMPARE RELAYS for the same module
#   for module in modules:
#     hname  = os.path.join(indir,f"Relay$R/trigstudy_krms4.root:{module}/Eprof_vs_trigphase")
#     hnames = { r: hname.replace('$R',r) for r in relays }
#     module = module.replace('_','-')
#     text   = module
#     ptag   = f"_relays_Eprof-tp_{module.replace('WX_IH00','-')}{tag}"
#     comparehists(hnames,ptag,text,xmin=tmin,xmax=tmax,
#                  ymin=0,ymax=38,header="Relay",lumi=lumi)
#     comparehists(hnames,ptag+"_norm",text,xmin=tmin,xmax=tmax,
#                  ymin=0,ymax=0.07,header="Relay",lumi=lumi,norm=True)
#   
#   # COMPARE MODULES for the same relay
#   for relay in relays:
#     hname  = os.path.join(indir,f"Relay{relay}/trigstudy_krms4.root:$M/Eprof_vs_trigphase")
#     hnames = {
#       m.replace('WX_IH00','*').replace('_','-'): hname_.replace('$M',m) for m in modules
#     }
#     text   = f"Relay {relay}"
#     lumi_  = f"{relay} {lumi}"
#     ptag   = f"_modules_Eprof-tp_R{relay}{tag}"
#     comparehists(hnames,ptag,text,xmin=tmin,xmax=tmax,
#                  ymin=0,ymax=38,header="Module",lumi=lumi_)
#     comparehists(hnames,ptag+"_norm",text,xmin=tmin,xmax=tmax,
#                  ymin=0,ymax=0.07,header="Module",lumi=lumi_,norm=True)
#   
#   # COMPARE ROCs
#   irocs = [ '0', '1', '2' ]
#   for relay in relays:
#     for module in modules:
#       hname  = os.path.join(indir,f"Relay{relay}/trigstudy_krms4.root:{module}/Eprof_vs_trigphase_roc$i")
#       hnames = { f"All": hname.replace('_roc$i','') }
#       hnames.update({ f"ROC {i}": hname.replace('$i',i) for i in irocs })
#       module = module.replace('_','-')
#       text   = module
#       ptag   = f"_rocs_Eprof-tp_R{relay}_{module}{tag}"
#       lumi_  = f"{relay} {lumi}"
#       comparehists(hnames,ptag,text,xmin=tmin,xmax=tmax,
#                    ymin=0,ymax=38,lumi=lumi_)
#       comparehists(hnames,ptag+"_norm",text,xmin=tmin,xmax=tmax,
#                    ymin=0,ymax=0.07,lumi=lumi_,norm=True)
  
  # PLOT TRIGGER WINDOWS
  kvals = [ '4' ]
  for relay in relays:
    for module in modules:
      for krms in kvals:
        path   = os.path.join(indir,f"Relay{relay}/trigstudy_krms{krms}.root:{module}/")
        module = module.replace('_','-')
        ptag   = f"_R{relay}_{module}{tag}_krms{krms}"
        lumi_  = f"Relay {relay} {lumi}"
        text   = f"Module {module.replace('_','-')}"
        plotTrigTimeWindow(path,vstag="_vs_channel",tag=ptag,lumi=lumi_,text=text)
        plotTrigTimeWindow(path,vstag="_vs_roc",tag=ptag,lumi=lumi_,text=text)
  
#   # COMPARE KRMS
#   kvals = [ '2', '3', '4', '5' ]
#   for relay in relays:
#     for module in modules:
#       hname  = os.path.join(indir,f"Relay{relay}/trigstudy_krms$K.root:{module}/Eprof_vs_trigphase")
#       hnames = { f"krms = {k}": hname.replace('$K',k) for k in kvals }
#       module = module.replace('_','-')
#       text   = module
#       ptag   = f"_krms_Eprof-tp_R{relay}_{module}{tag}"
#       lumi_  = f"{relay} {lumi}"
#       comparehists(hnames,ptag,text,xmin=tmin,xmax=tmax,
#                    ymin=0,ymax=38,lumi=lumi_)
#       comparehists(hnames,ptag+"_norm",text,xmin=tmin,xmax=tmax,
#                    ymin=0,ymax=0.07,lumi=lumi_,norm=True)
  

if __name__ == '__main__':
  from argparse import ArgumentParser
  relays = [
    1726347199,
    1726518879,
    1726593188,
    1726954855,
    1727132796,
    1727204018,
    1727206292,
  ]
  modules = [
    'ML_F3WX_IH0014',
    'ML_F3WX_IH0016',
    'ML_F3WX_IH0017',
    'ML_F3WX_IH0018',
    'ML_F3WX_IH0019',
    'ML_F3WX_IH0020',
    #'ML_F3WX_IH0015',
    #'ML_R3WX_42QH00006',
  ]
  parser = ArgumentParser(description="Plot & compare histograms",epilog="Good luck!")
  parser.add_argument('-r', "--relays", type=int, default=relays,
                      help="relay numbers to compare, default=%(default)" )
  parser.add_argument('-m', "--modules", type=int, default=modules,
                      help="module numbers to compare, default=%(default)" )
  parser.add_argument('-k', "--krms", type=int,
                      help="krms values, default=%(default)" )
  parser.add_argument('-i', "--indir",  default='calibrations',
                      help="input directory, default=%(default)r" )
  parser.add_argument('-t', "--tag", default="",
                      help="extra tag for output files" )
  parser.add_argument('-L', "--lumitext",  default="(Testbeam 2024)",
                      help="extra luminosity label on plot, default=%(default)r" )
  parser.add_argument('-o', "--outdir", default='plots',
                      help="output directory for JSON file, default=%(default)r" )
  args = parser.parse_args()
  main(args)
    
