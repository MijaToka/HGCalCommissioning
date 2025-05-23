import sys
sys.path.append("./")
from HGCalCalibration import HGCalCalibration
import DigiAnalysisUtils as DAU
import HexPlotUtils as HPU
import numpy as np
import json
import ROOT

class HGCalPedestalsClosure(HGCalCalibration):

    def __init__(self, raw_args=None):
        
        self.histofiller = self.histoFillerForClosure
        ROOT.gInterpreter.Declare('#include "interface/helpers.h"')
        super().__init__(raw_args)

    @staticmethod
    def definePedestalsClosureRDF(task_spec):
        """defines the RDataFrame with the selections / variables needed for the closure of pedestals"""

        rdf = ROOT.RDF.Experimental.FromSpec(task_spec)
        ROOT.RDF.Experimental.AddProgressBar(rdf)
    
        #filter out data for the fed/readout sequence corresponding to a single module
        rdf = rdf.DefinePerSample("target_module_fed", 'rdfsampleinfo_.GetI("fed")') \
                .DefinePerSample("target_module_seq", 'rdfsampleinfo_.GetI("seq")') \
                .Define('good_rechit',   'HGCHit_flags==0 && HGCDigi_chType>=0') \
                .Define('target_module', 'HGCDigi_fedId==target_module_fed && HGCDigi_fedReadoutSeq==target_module_seq') \
                .Define('maskhit',       'good_rechit & target_module') \
                .Define('ch',            'HGCDigi_channel[maskhit]') \
                .Define('en',            'HGCHit_energy[maskhit]') \
                .Define('rocidx',        f'sumOverRoc(ch,en,0)') \
                .Define('nchperroc',     f'sumOverRoc(ch,en,1)') \
                .Define('dsen',          f'sumOverRoc(ch,en,2)') \
                .Define('asen',          f'sumOverRoc(ch,en,3)') \
                .Define('modulecm',      'HGCDigi_cm[maskhit]') \
                .Define('cm2',           'commonMode(modulecm,2)')

        return rdf
    
        
    @staticmethod
    def histoFillerForClosure(args):
        """defines the filling of the histograms for closure tests of the pedestal"""
        
        outdir, module, task_spec, cmdargs = args
        
        #read #rocs and #eErx from first task
        with open(task_spec) as json_data:
            samples = json.load(json_data)['samples']
            nerx = samples['data1']['metadata']['nerx']
            nch = nerx*37
            nrocs = int(nerx/2)
            
        #adjust binning from the extremes
        minirdf = HGCalPedestalsClosure.definePedestalsClosureRDF(task_spec)
        minirdf = minirdf.Range(1000)
        obslist = ['en', 'cm2', 'dsen', 'asen']
        obsbounds  = [minirdf.Min(x) for x in obslist]
        obsbounds += [minirdf.Max(x) for x in obslist]
        obsbounds += [minirdf.Mean(x) for x in obslist]
        ROOT.RDF.RunGraphs(obsbounds)
        bindefs={
            'ch' : (nch,-0.5,nch-0.5),
            'rocs' : (nrocs,-0.5,nrocs-0.5),
            'rocch' : (75,-0.5,74.5)
        }
        for i,obs in enumerate(obslist):
            minobs = int(obsbounds[i].GetValue()) - 0.5
            maxobs = int(obsbounds[i+len(obslist)].GetValue()) + 0.5
            try:
                nobs = int(maxobs - minobs)
                if obs in ['dsen', 'asen']:
                    nobs = min(nobs,256)
                elif nobs>512:
                    avgobs = int(obsbounds[i+2*len(obslist)].GetValue())
                    minobs = avgobs-256.5
                    maxobs = avgobs+256.5
                    nobs = int(maxobs - minobs)
                bindefs[obs]=(nobs,minobs,maxobs)
            except Exception as e:
                print(f'Could not define binning for {obs} in {module}')
                print(e)
                pass
        print(f'Bins determined from sub-sample: {bindefs}')
        
        #fill the histograms with full statistics
        rdf = HGCalPedestalsClosure.definePedestalsClosureRDF(task_spec)
        profiles = [
            rdf.Histo3D(("envscm",    ';Channel;RecHit energy;CM2',*bindefs['ch'],   *bindefs['cm2'],   *bindefs['en']), "ch", "cm2", "en"),
            rdf.Histo2D(("nchperroc", ';ROC;#channels used',       *bindefs['rocs'], *bindefs['rocch']), "rocidx", "nchperroc"),
            rdf.Histo2D(("dsen",      ';ROC;DS energy',            *bindefs['rocs'], *bindefs['dsen']),  "rocidx", "dsen"),
            rdf.Histo2D(("asen",      ';ROC;AS energy',            *bindefs['rocs'], *bindefs['asen']),  "rocidx", "asen")
        ]    
        ROOT.RDF.RunGraphs(profiles)
    
        #write histograms to file
        rfile=f'{outdir}/{module}_closure.root'
        fOut=ROOT.TFile.Open(rfile,'RECREATE')
        fOut.cd()
        for p in profiles:
            obj=p.GetValue()
            obj.SetDirectory(fOut)
            obj.Write()
        fOut.Close()
        print(f'Histograms available in {rfile}')
    
        return (module,rfile)
        
    def addCommandLineOptions(self,parser):
        parser.set_defaults(output='calibrations_closure')
        self.parser.add_argument("-p", "--pedestals", type=str,
                                 help='original pedestals file',
                                 default=None, required=True)

    @staticmethod
    def analyze(args):
        """profiles the Channel vs ADC vs CM histogram to find pedestals to use"""

        typecode, url, cmdargs = args
        if not '_closure' in url : return {}
        typecode = typecode.replace('_closure','')
        
        #summary of pedestals and noise                
        results = DAU.profile3DHisto(url,'envscm')
        
        cm_rms = np.array(results['Y_rms'])
        en_loc = np.array(results['Z_mean'])
        en_rms = np.array(results['Z_rms'])
        rho = np.array(results['YZ_rho'])
        noslope = np.zeros_like(rho)
        isvalid = (cm_rms>1e-3)
        cm_slope =  -5*np.ones_like(en_loc)
        np.divide(rho*en_rms, cm_rms, out=cm_slope, where=isvalid)
        
        #fraction of coherent noise per roc
        nch = np.array(DAU.profile2DHisto(url,'nchperroc')['Y_mean'])
        dsum_rms = np.array(DAU.profile2DHisto(url,'dsen')['Y_rms'])
        asum_rms = np.array(DAU.profile2DHisto(url,'asen')['Y_rms'])
        inc_noise = asum_rms / np.sqrt(nch)
        delta2 = dsum_rms**2 - asum_rms**2
        coh_noise = np.sign(delta2)*np.sqrt( np.abs(delta2) ) / nch
        cnf = coh_noise/inc_noise

        results = {
            'Typecode' : typecode.replace('_','-'),
            'hit_ped'  : en_loc.tolist(),
            'hit_rms'  : en_rms.tolist(),
            'hit_cm_slope' : cm_slope.tolist(),
            'inc_Noise' :  np.ravel( [ np.ones(2)*x for x in inc_noise] ).tolist(),
            'coh_Noise' : np.ravel( [ np.ones(2)*x for x in coh_noise] ).tolist(),
            'cnf' : np.ravel( [ np.ones(2)*x for x in cnf] ).tolist()
        }

        return results


    def createCorrectionsFile(self, results):
        
        """ final tweaks of the analysis results to export as a json file for CMSSW """

        #load original pedestals file and add the closure information to it
        with open(self.cmdargs.pedestals,'r') as stream:
            pedestals = json.load(stream)            
        for r in results:
            if not 'Typecode' in r : continue
            typecode = r.pop('Typecode').replace('-','_')
            pedestals[typecode].update(r)

        jsonurl = self.cmdargs.pedestals.replace('.json','_with_closure.json')
        with open(jsonurl,'w') as outfile:
            json.dump(pedestals,outfile,sort_keys=False,indent=2)
            
        return jsonurl


if __name__ == '__main__':

    import argparse
    import os
    
    #as this script is not strictly used for calibration and only requires a NANO file, the arguments are parsed directly
    #to build a scan map directly so that HGCALCalibration can proceed directly
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input",     help='input NANO file',             default=None, type=str, required=True)
    parser.add_argument("-p", "--pedestals", help='pedestals file being tested', default=None, type=str, required=True)
    parser.add_argument("-o", "--output",    help='output directory (same as pedestals if not specified)', default=None, type=str)
    args = parser.parse_args()

    #output (same as pedestals file)
    output = os.path.dirname(args.pedestals) if args.output is None else args.output
    os.makedirs(output,exist_ok=True)
        
    #encapsulate input as a scanmap    
    scanmap = { "closure": { "idx":0, "input": [args.input], "params":{} } }
    scanmap_url = f'{output}/scanmap.json'
    with open(scanmap_url,'w') as outfile:
            json.dump(scanmap,outfile,sort_keys=False,indent=2)

    #call closure
    raw_args = ['--scanmap', scanmap_url, '-o', output, '-p', args.pedestals, '--forceRewrite', '--skipHistoFiller']
    pedestalclosure = HGCalPedestalsClosure(raw_args)
