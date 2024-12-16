import sys
import ROOT
import argparse
import json
from HGCalCommissioning.LocalCalibration.plot.wafer import fill_wafer_hist

def createCalibHexPlotSummary(jsonfile : str, outputfile : str) :
    """
    Opens a json calibration file and fills the appropriate hexplots for every parameter
    the result is stored in a ROOT file where each folder corresponds to a different module
    """

    #open the calibration json
    with open(jsonfile,'r') as fin:
        calibs_dict = json.load(fin)

    #fill hex plots for every parameter and save to ROOT file
    fOut = ROOT.TFile.Open(outputfile,'RECREATE')
    def _saveAsHexPlot(values,moduletype,hname,htitle,dOut):
        h = fill_wafer_hist(values,moduletype)
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
