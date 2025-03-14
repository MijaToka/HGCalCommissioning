import glob
import re
import json
import numpy as np
import pandas as pd #type: ignore
import copy
try:
    import ROOT #type: ignore
except:
    print('Looks like ROOT is not available you can get it sourcing a LCG environment')
    print('source /cvmfs/sft.cern.ch/lcg/views/LCG_105a/x86_64-el9-gcc13-opt/setup.sh')
    print('The script will probably fail after this message...')

import argparse

def groupDQMFiles(url : str) -> dict:
    """looks for DQM files and groups them by relay"""

    files_per_run : dict = {}
    for f in glob.glob(f'{url}/DQM*.root'):
        lumi, run = re.findall('.*/DQM_V(\\d+)_HGCAL_R(\\d+).root',f)[0]
        lumi=int(lumi)
        run=int(run)
        if not run in files_per_run:
            files_per_run[run] = {}
        files_per_run[run][lumi] = f
    return files_per_run

def buildDQMSummaryFrom(files_per_run : dict) :
    """reads the quality flag histograms and fills a dataframe with the counts"""

    data = []
    for run, dqm_nibbles in files_per_run.items():
        
        fed_data={}
        econ_data={}
        pedestal_data={}
        
        for lumi, url in dqm_nibbles.items():

            fIn=ROOT.TFile.Open(url,'READ')

            #read the FED flags (in earlier versions this may be absent)
            hfed = fIn.Get(f'DQMData/Run {run}/HGCAL/Run summary/Digis/fedQualityH')
            hfedpayload = fIn.Get(f'DQMData/Run {run}/HGCAL/Run summary/Digis/fedPayload')
            try:
                nbinsx = hfed.GetNbinsX()
                for xbin in range(hfed.GetNbinsX()):
                
                    fedid = '%d'%(hfed.GetXaxis().GetBinCenter(xbin+1))
                    if not fedid in fed_data:
                        fed_data[fedid] = {'lumi':[], 'avgpayload':[], 'rmspayload':[], 'events':[] }
                    
                    payload = hfedpayload.ProjectionY('projy',xbin+1,xbin+1)
                    fed_data[fedid]['lumi'].append(lumi)
                    fed_data[fedid]['avgpayload'].append(payload.GetMean())
                    fed_data[fedid]['rmspayload'].append(payload.GetRMS())
                    fed_data[fedid]['events'].append(payload.GetEntries())
                    payload.Delete()
                    
                    for ybin in range(hfed.GetNbinsY()):
                        flaglabel = hfed.GetYaxis().GetBinLabel(ybin+1)
                        if not flaglabel in fed_data[fedid]:
                            fed_data[fedid][flaglabel] = []
                        fed_data[fedid][flaglabel].append( hfed.GetBinContent(xbin+1,ybin+1) )
            except:
                pass
            
            #read the ECON-D and Capture Block flags
            hecon = fIn.Get(f'DQMData/Run {run}/HGCAL/Run summary/Digis/econdQualityH')
            hcb = fIn.Get(f'DQMData/Run {run}/HGCAL/Run summary/Digis/cbQualityH')
            hpayload = fIn.Get(f'DQMData/Run {run}/HGCAL/Run summary/Digis/econdPayload')
            modname2idx = {}
            for xbin in range(hecon.GetNbinsX()):
                    
                modname = hecon.GetXaxis().GetBinLabel(xbin+1)
                modname2idx[modname] = xbin
                if not modname in econ_data:
                    econ_data[modname] = {'lumi':[], 'avgpayload':[], 'rmspayload':[], 'events':[] }
                    
                payload = hpayload.ProjectionY('projy',xbin+1,xbin+1)
                econ_data[modname]['lumi'].append(lumi)
                econ_data[modname]['avgpayload'].append(payload.GetMean())
                econ_data[modname]['rmspayload'].append(payload.GetRMS())
                econ_data[modname]['events'].append(payload.GetEntries())
                payload.Delete()
                    
                for ybin in range(hcb.GetNbinsY()):
                    flaglabel = 'CB:'+hcb.GetYaxis().GetBinLabel(ybin+1)
                    if not flaglabel in econ_data[modname]:
                        econ_data[modname][flaglabel] = []
                    econ_data[modname][flaglabel].append( hcb.GetBinContent(xbin+1,ybin+1) )

                for ybin in range(hecon.GetNbinsY()):
                    flaglabel = 'ECON:'+hecon.GetYaxis().GetBinLabel(ybin+1)
                    if not flaglabel in econ_data[modname] :
                        econ_data[modname][flaglabel] = []
                    econ_data[modname][flaglabel].append( hecon.GetBinContent(xbin+1,ybin+1) )

            #read pedestals
            for modname, modidx in modname2idx.items():
                avgadc = fIn.Get(f"DQMData/Run {run}/HGCAL/Run summary/Digis/avgadc_module_{modidx}")
                vals = np.array([avgadc.GetBinContent(xbin+1) for xbin in range(avgadc.GetNbinsX())])
                q = np.percentile(vals,[16,50,84])
                if not modname in pedestal_data:
                    pedestal_data[modname] = {'lumi':[], 'minpedestal':[], 'q16pedestal':[], 'medpedestal':[], 'q84pedestal':[], 'maxpedestal':[] }
                pedestal_data[modname]['lumi'].append(lumi)
                pedestal_data[modname]['minpedestal'].append(vals.min())
                pedestal_data[modname]['q16pedestal'].append(q[0])
                pedestal_data[modname]['medpedestal'].append(q[1])
                pedestal_data[modname]['q84pedestal'].append(q[2])
                pedestal_data[modname]['maxpedestal'].append(vals.max())

            fIn.Close()

        #finalise by sorting the timeline and converting to numpy arrays
        for report in [fed_data,econ_data,pedestal_data]:
            for k in report.keys():
                idxsort = np.argsort(report[k]['lumi'])
                for v,arr in report[k].items():
                    report[k][v] = np.array(arr)[idxsort]

        data.append( [run, copy.deepcopy(fed_data), copy.deepcopy(econ_data), copy.deepcopy(pedestal_data)] )
            
    df = pd.DataFrame(data, columns=['Run','FED','ECON-D','Pedestals'] )
    return df

def main():

    parser = argparse.ArgumentParser(prog='dqm collector builder',
                                     description='opens different DQM files and builds a dataframe with a meaningful summary',
                                     epilog='Developed for HGCAL system tests')
    parser.add_argument('-i', '--input',
                        default='/eos/cms/store/group/dpg_hgcal/tb_hgcal/2025/hgcalrd/Test/Relay1739467847/c00a3ad4-eedc-11ef-a574-b8ca3af74182/prompt',
                        help='Base directory for a Run with DQM files', type=str)
    parser.add_argument('-o', '--output',
                        default='{basedir}/reports/dqmcollector.feather',
                        help='Output file', type=str)
    args = parser.parse_args()


    inputdirs = []
    if not 'Relay' in args.input and not 'Run' in args.input:
        for url in glob.glob(f'{args.input}/Relay*/*/*'):
            inputdirs.append(url)        
    else:
        inputdirs.append(args.input)
        
    for indir in inputdirs:

        files_per_run = groupDQMFiles(indir)
        print(f'Collected files for {len(files_per_run)} run(s) @ {indir}')

        df = buildDQMSummaryFrom(files_per_run)
        localoutput = args.output
        if '{basedir}' in localoutput:
            localoutput = localoutput.format(basedir=indir)
        df.to_feather(localoutput)
        print(f'Saved DQM collector table in {localoutput} with shape={df.shape}')

if __name__ == '__main__':
    main()
