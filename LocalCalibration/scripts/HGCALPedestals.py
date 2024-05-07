from HGCALCalibration import HGCALCalibration
#import PedestalCorrectionsMaker
import ROOT
import os
import pandas as pd
import time
import itertools
import json
from HGCalCommissioning.LocalCalibration.JSONEncoder import CompactJSONEncoder

class HGCALPedestals(HGCALCalibration):
        #methods
    def analyse(self):
        pass
        
    #no se llama para los objetos   
    @staticmethod 
    def parseArguments():
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--input",
                        help='input directory=%(default)s',
                        default="/eos/cms/store/group/dpg_hgcal/tb_hgcal/2023/CMSSW/ReReco_Oct10/")
        parser.add_argument("--maxModules",
                        help='process this max. number of modules=%(default)s',
                        default=2, type=int)
        parser.add_argument("--maxFiles",
                        help='process this max. number of files=%(default)s',
                        default=-1, type=int)
        parser.add_argument("-r", "--run",
                        help='run number=%(default)s',
                        default=1695472275)
        parser.add_argument("-o", "--output",
                        help='output directory default=%(default)s',
                        default='./calibrations')
        parser.add_argument("-g", "--gain", type=int, choices=[80, 160, 320],
                        help='gain number in fC default=%(default)s',
                        default=80)
    #This was the correction lib json file
    #parser.add_argument("--json",
    #                    help='final json output default=%(default)s',
    #                    default='./etc/pedestals.json.gz')
       
        return parser.parse_args()
    #correction tiene que ser el main de pedestal_corrections_maker
    def corrections(self):
        #PedestalCorrectionsMaker.main()
        args = HGCALPedestals.parseArguments()
        #prepare output
        os.system(f'mkdir -p {args.output}')
    	#We might have to propose a name for the file RunNumber_RunType_TimeStamp ?
    	#We actually want to create a txt file to be used by the macro RAW-DIGI-RECO
        outfile=os.path.join(args.output,f'Pedestals_Run_{args.run}.root')
    	#jsonurl=args.json
    
    	#profile pedestals if input is directory    
        if os.path.isdir(args.input):
        	run=int(args.run)
        	#metadata=getNANOInputsForRun(run,tbdir=args.input,maxFiles=args.maxFiles)
        	#Write a function to the the directory with RECO and NANO root files. 
        	metadata=self.getNANOFiles(run,tbdir=args.input,maxFiles=args.maxFiles)
        	tstart = time.time()
        	self.profilePedestals(url=metadata['files'],outfile=outfile,maxModules=args.maxModules)
        	tend = time.time()
        	print(f'Time spent profiling pedestals: {tend-tstart:3.3f}s')
        else:
        	outfile=args.input

    	#create corrections
        tstart = time.time()
        print("Corrections method, after time ")
        self.createCorrectionJson(outfile)
        tend = time.time()        
        print(f'Time spent creating final corrections: {tend-tstart:3.3f}s')

    #print(f'Corrections available in {jsonurl}')
        #Method to process events and compute pedestals & CM corrections       
    def profilePedestals(self, url, outfile, maxModules=2):
    
        ROOT.gROOT.ProcessLine('#include "interface/helpers.h"') 
        # This activates implicit multi-threading  
        ROOT.ROOT.EnableImplicitMT()
        #url is the ROOT file of flist defined in getNANOFiles and Event is the tree inside the *NANO.root file
        df = ROOT.RDataFrame('Events',url)
        df = df.Define(f'HGC_ch',       f'HGC_roc*74+HGC_half*37+HGC_halfrocChannel') \
               .Define(f'HGC_module',   f'HGC_econdIdx+HGC_captureBlock+HGC_fedId') \
               .Define(f'HGC_erx',      f'HGC_roc*2+HGC_half') \
               .Define(f'HGCCM_module', f'HGCCM_econdIdx+HGCCM_captureBlock+HGCCM_fedId') \
               .Define(f'HGCCM_erx',    f'HGCCM_roc*2+HGCCM_half') \
               .Define(f'HGC_avgcm',    f'assignAveragedCM(HGC_module,HGC_erx,HGCCM_module,HGCCM_erx,HGCCM_cm)')

        histos=[]
        for econd in range(maxModules):
          df=df.Define(f'module_{econd}', f'HGC_module=={econd}') \
               .Define(f'ADC_{econd}',    f'HGC_adc[module_{econd}]') \
               .Define(f'ch_{econd}',     f'HGC_ch[module_{econd}]') \
               .Define(f'AvgCM_{econd}',  f'HGC_avgcm[module_{econd}]')

          #Make 3D histogram : channel vs CM vs ADC
          histos.append(
            df.Histo3D((f"chcmadc_{econd}", f";Channel;CM;ADC;Events", 222,-0.5,221.5,400,0.5,400.5,400,0.5,400.5),
                        f"ch_{econd}", f"AvgCM_{econd}", f"ADC_{econd}")
                       )

        #Save profiles to output file
        fOut=ROOT.TFile.Open(outfile,'RECREATE')
        for h in histos:
          h.Write()
        fOut.Close()

        ROOT.ROOT.DisableImplicitMT()

    #Method to summarize the pedestals and correlation with CM
    def createCorrectionJson(self, url, jsonurl=None, gain=80):

        if jsonurl is None: jsonurl=f'etc/pedestals_{gain}fC.json.gz'

        correctors={}
        #cor_list = ['pedestal','cm','rho','noise']
        cor_list = ['ADC_ped', 'CM_ped', 'CM_slope', 'Noise', 'BXm1_slope']
        #Project the TH3 to get the average values and correlation factors with CM per channel
        fIn=ROOT.TFile.Open(url)
        for k in fIn.GetListOfKeys():
          hname=k.GetName()
          h=k.ReadObj()
          #Define the modulo
          mod=int(hname.split('_')[-1])
          typecode = 'ML-F3PT-TX-0003'

          h=fIn.Get(f'chcmadc_{mod}')

          #hold the values per channel of this module
          cor_values= dict( [(k,[]) for k in cor_list + ['Channel'] ] )

          ny,ymin,ymax=h.GetNbinsY(),h.GetYaxis().GetXmin(),h.GetYaxis().GetXmax()
          nz,zmin,zmax=h.GetNbinsZ(),h.GetZaxis().GetXmin(),h.GetZaxis().GetXmax()
          h2=ROOT.TH2F('cmvsadc','',ny,ymin,ymax,nz,zmin,zmax)

          for xbin in range(h.GetNbinsX()):

            h2.Reset('ICE')
            #print(f"valores {ny} {nz}")
            for ybin,zbin in itertools.product(range(ny),range(nz)):
              h2.SetBinContent(ybin+1,zbin+1, h.GetBinContent(xbin+1,ybin+1,zbin+1) )

            #cor_values['ch'].append( h.GetXaxis().GetBinLowEdge(xbin+1) )
            cor_values['Channel'].append( h.GetXaxis().GetBinLowEdge(xbin+1) )
            #cor_values['pedestal'].append( h2.GetMean(2) )
            cor_values['ADC_ped'].append( h2.GetMean(2) )
            #cor_values['noise'].append( h2.GetRMS(2) )
            cor_values['Noise'].append(h2.GetRMS(2))
            #cor_values['cm'].append( h2.GetMean(1) )
            cor_values['CM_ped'].append( h2.GetMean(1) )
            #cor_values['rho'].append( h2.GetCorrelationFactor() )
            cor_values['CM_slope'].append( h2.GetCorrelationFactor() )
            cor_values['BXm1_slope'].append(0.)

          cor_values['Channel'].append( h.GetXaxis().GetBinUpEdge(xbin+1) )

          h2.Delete()

          correctors[typecode] = {'Channel': cor_values['Channel'],
			     'ADC_ped':  cor_values['ADC_ped'] ,
			     'Noise':  cor_values['Noise'] ,
                             'CM_ped':  cor_values['CM_ped'] ,
		             'CM_slope':  cor_values['CM_slope'] ,
		   	     'BXm1_slope':  cor_values['BXm1_slope']
                            }

        #import pandas as pd
        #a=[]
        #for mod in correctors.keys():
        #    chlist=[c for c in range(len(correctors[mod]['noise'].edges)-1)]
        #    a.append( [mod]+[ correctors[mod][k].content for k in cor_list] + [chlist] )
        #print("VALOR DE A", a)
        #df=pd.DataFrame(a,columns=['module']+cor_list+['channel'])
        #df=df.explode( cor_list+['channel'] )
        #df.to_csv(jsonurl.replace('.json.gz','.csv'),sep=' ',index=False)

        with open(jsonurl,'w') as outfile:
            json.dump(correctors,outfile,cls=CompactJSONEncoder,sort_keys=False,indent=2)


if __name__ == '__main__':

    pedestal = HGCALPedestals()
    pedestal.corrections()
