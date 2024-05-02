import sys
import pandas as pd
import ROOT
import argparse

def fillHexPlot(ch_values,moduletype='LD_full'):

    """
    this method takes care of instatiating a hexplot for a given module type and fill it with the values for the required channels
    ch_values is a dict of (channel number, value)
    module_type is a string with the module type to be used in the hexplot
    """
    
    #create the hexplot
    hex_plot = ROOT.TH2Poly()
    hex_plot.SetDirectory(0)
    fgeo=ROOT.TFile.Open(f'/eos/cms/store/group/dpg_hgcal/comm_hgcal/ykao/geometry_{moduletype}_wafer_20230919.root','R')
    i=0
    for key in fgeo.GetListOfKeys():
        obj = key.ReadObj()
        if not obj.InheritsFrom("TGraph") : continue
        hex_plot.AddBin(obj)
        
        idx = int(i - (i / 39) * 2);
        #isCM = i%39 in [37,38]
        if idx in ch_values:
            hex_plot.SetBinContent(i+1,ch_values[idx])
        i+=1
        
    fgeo.Close()

    return hex_plot
    

def main():

    #parse command line
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--moduletype",
                        help='module type=%(default)s',
                        default="LD_full")
    parser.add_argument("-i", "--input",
                        help='input CSV file with channel and data columns=%(default)s',
                        default=None)
    parser.add_argument("-o", "--output",
                        help='output file with hexplotsdefault=%(default)s',
                        default='./hexplots.root')
    args = parser.parse_args()

    #fill a dataframe from a csv file
    df=pd.read_csv(args.input,sep='\s+',header='infer')
    df=df.set_index('channel')

    #fill plots for every column in the dataframe and save to ROOT file
    fOut=ROOT.TFile.Open(args.output,'RECREATE')
    for c in df.columns:
        if c.lower()=='channel' : continue
        ch_values=df[c].to_dict()
        h=fillHexPlot(ch_values=ch_values,moduletype=args.moduletype)
        fOut.cd()
        h.SetName(c)
        h.SetDirectory(fOut)
        h.Write()
    fOut.Close()
    
if __name__ == '__main__':    
    sys.exit(main())
