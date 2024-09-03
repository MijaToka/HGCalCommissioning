import sys
import ROOT
import argparse
import json
    
def fillHexPlot(ch_values,moduletype='ML_L'):

    """
    this method takes care of instatiating a hexplot for a given module type and fill it with the values for the required channels
    ch_values is a dict of (channel number, value)
    module_type is a string with the module type to be used in the hexplot
    """
    
    #create the hexplot
    hex_plot = ROOT.TH2Poly()
    hex_plot.SetDirectory(0)
    fgeo=ROOT.TFile.Open(f'../DQM/data/geometry_{moduletype}_wafer.root','R')
    iobj=0
    for key in fgeo.GetListOfKeys():
        obj = key.ReadObj()
        if not obj.InheritsFrom("TGraph") : continue

        #ignore CM
        isCM = (iobj % 39 == 37) or (iobj % 39 == 38)
        if isCM :
            iobj += 1
            continue

        hex_plot.AddBin(obj)
        
        eRx = int(iobj/39)
        idx = iobj - eRx*2 #take out 2 CM per eRx to get the proper idx
        if idx < len(ch_values):
            hex_plot.SetBinContent(idx+1,ch_values[idx])
        else:
            raise ValueError(f'Length of values {len(ch_values)} does not accomodate for #obj={iobj} eRx={eRx} idx={idx}')

        iobj+=1
        
    fgeo.Close()

    return hex_plot
    
def createCalibHexPlotSummary(jsonfile : str, outputfile : str) :
    """
    opens a json calibration file and fills the appropriate hexplots for every parameter
    the result is stored in a ROOT file where each folder corresponds to a different module
    """

    #open the calibration json
    with open(jsonfile,'r') as fin:
        calibs_dict = json.load(fin)

    #fill hex plots for every parameter and save to ROOT file
    fOut=ROOT.TFile.Open(outputfile,'RECREATE')
    def _saveAsHexPlot(values,moduletype,hname,htitle,dOut):
        h=fillHexPlot(values,moduletype)
        h.SetName(hname)
        h.SetTitle(htitle)
        dOut.cd()
        h.SetDirectory(dOut)
        h.Write()
    for m in calibs_dict:
        fOut.cd()
        dOut = fOut.mkdir(m)
        moduletype = m[0:4].replace('-','_')
        for k,v in calibs_dict[m].items():
            if type(v[0])==list:
                for ik, vv in enumerate(v):
                    h=_saveAsHexPlot(vv,moduletype,f'{k}_{ik}',m,dOut)
            else:
                _saveAsHexPlot(v,moduletype,k,m,dOut)    
    fOut.Close()
    print(f'Summary plots from {jsonfile} have been stored in {outputfile}')

def main():

    #parse command line
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--json",
                        help='input json file with calibration data=%(default)s',
                        default=None)
    parser.add_argument("-o", "--output",
                        help='output file with hexplotsdefault=%(default)s',
                        default='./hexplots.root')
    args = parser.parse_args()

    createCalibHexPlotSummary(jsonfile=args.json, outputfile=args.output)

if __name__ == '__main__':    
    sys.exit(main())
