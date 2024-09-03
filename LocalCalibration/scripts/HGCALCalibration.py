import pandas as pd
import glob
import argparse
import os
from abc import ABC, abstractmethod
import ROOT
import json
from multiprocessing import Pool
import sys
sys.path.append("./")
from DigiAnalysisUtils import baseHistoFiller


class HGCALCalibration(ABC):
    """HGCALCalibration is a base class which can be used for procedures which make use of the NANO to fill histograms
    from where different quantities can be derived. The class will execute the analysis flow when it's `__init__` method is called
    in the following order:
    
    * histogram filling: at this point the input files and relevant parameters (e.g. of a scan) are determined, the filling of the histograms per module is performed. This step may be skipped with `--skipHistoFiller`
    * histogram analysis: at this point the analysis of the resulting histograms is performed
    * create corrections: the results of the analysis are collected and used to create a corrections file
    
    The derived classes need to implement the following methods (which can be just empty)
    
    * addCommandLineOptions : used to augment the arguments to be parsed from command line
    * buildScanParametersDict : used to identify specific parameters which were used to generate each NANO file 
    * analyze : the method that analyzes the the histograms and build the tables of constants
    * createCorrectionsFile : the method that makes use of the results to create a file
    """
 
    def __init__ (self):
        """Constructor of HGCALCalibration class"""

        #parse arguments and add as class attributes
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-i", "--input",
                                help='input directory=%(default)s',
                                default="/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/TB2024/")
        self.parser.add_argument("--moduleList",
                                help='process only these modules (csv list) %(default)s',
                                default='', type=str)
        self.parser.add_argument("-r", "--run", type=int,
                                help='run number=%(default)s',
                                default=1722725783)
        self.parser.add_argument("--maxThreads", type=int,
                                help='max threads to use=%(default)s',
                                default=8)
        self.parser.add_argument("-o", "--output",
                                help='output directory default=%(default)s',
                                default='./calibrations')
        self.parser.add_argument("--forceRewrite",
                                help='force re-write of previous output=%(default)s',
                                action='store_true')
        self.parser.add_argument("--skipHistoFiller",
                                 help='skip filling of the histograms=%(default)s',
                                 action='store_true')
        self.parser.add_argument("--nanoTag",
                                 help='nano version tag to use, if empty use latest default=%(default)s',
                                 default='',
                                 action='store_true')        
        self.addCommandLineOptions(self.parser)
        self.cmdargs = self.parser.parse_args()
        self.__dict__.update(self.cmdargs.__dict__)

        #run will always be appended to the output directory
        self.output=f'{self.output}/Run{self.run}'
        
        #histogram filling
        if not self.skipHistoFiller:

            #check if upper class has defined an histogram filler
            if not hasattr(self, 'histofiller'):
                print('Setting base histogram filler has an attribute')
                setattr(self,'histofiller',baseHistoFiller)

            #prepare the jobs (run info#modules, sub-samples, etc.)
            self.prepareHistogramFiller(self.cmdargs.nanoTag)

            #launch tasks
            ntasks=len(self.histofill_tasks)        
            with Pool(self.maxThreads) as p:
                task_results=p.map(getattr(self,'histofiller'), self.histofill_tasks)
            print('Histo filling',task_results)

        #analysis of histograms
        rootfiles = glob.glob(f'{self.output}/histofiller/*.root')
        tasklist = [ (os.path.splitext(os.path.basename(url))[0], url, self.cmdargs) for url in rootfiles ]
        with Pool(self.maxThreads) as p:
            results = p.map(self.analyze, tasklist)

        #crete the corrections based on the analysis results
        jsonurl = self.createCorrectionsFile(results)
        print(f'Corrections stored in {jsonurl}')
            
    @abstractmethod
    def addCommandLineOptions(parser : argparse.ArgumentParser):
        pass
        
    @abstractmethod
    def buildScanParametersDict(file_list : list, modules_list : list) -> dict:
        pass
    
    @staticmethod
    @abstractmethod
    def analyze(args):
        pass

    @abstractmethod
    def createCorrectionsFile(results : list) -> str:
        pass

    
    def prepareHistogramFiller(self, nanotag : str):
        """steers preparation of the analysis for a run (parse commandline, get run information, prepare output)"""

        #prepare output 
        os.makedirs(self.output + '/histofiller', exist_ok=self.forceRewrite)

        #get the run row in the run registry
        self.runrow = self.readRunRegistry()

        #get the appropriate nano version to run on
        promptdir=self.runrow['Output']
        basedir=promptdir.replace('/prompt','')
        nano_versions=[]
        for v in os.listdir(basedir):
            if v=='prompt' : continue
            nanodir=os.path.join(basedir,v)
            if not os.path.isdir(nanodir): continue
            if nanotag!='' and v!=nanotag: continue
            creation_time=os.path.getctime(nanodir)
            nano_versions.append( (nanodir,creation_time) )
        if len(nano_versions)==0:
            raise IOError(f'No nano directories found in {basedir} (preferred tag is {nanotag})')

        #sort by time, get latest
        nano_versions = sorted(nano_versions, key=lambda x: x[1], reverse=False)
        nanodir = nano_versions.pop()[0]
        #create tasks
        self.histofill_tasks = self.buildHistoFillerTasks(nanodir)

        
    def readRunRegistry(self) -> pd.core.series.Series:
        """reads the run registry and retrieves the information about this run"""

        #check if run registry is valid and open it
        runregfiles = glob.glob(f'{self.input}/runregistry*')
        if len(runregfiles)==0:
            raise OSError(f"No runregistry files in {self.input}")
        _, runreg_ext = os.path.splitext(runregfiles[0])
        if runreg_ext=='.csv':
            run_registry = pd.read_csv(runregfiles[0],sep='\s+', header='infer')
        elif runreg_ext=='.feather':
            run_registry = pd.read_feather(runregfiles[0])
        else:
            raise IOError(f'Unable to decode runregistry with {runreg_ext} extension')
        
        #get the run
        mask = (run_registry['Run']==self.run) & (run_registry['RecoValid']==True)
        if mask.sum()==0:
            raise ValueError(f'Unable to find {self.run} in run registry file')

        #return the latest one
        return run_registry.loc[mask].iloc[-1].copy()

    def buildHistoFillerTasks(self, nanodir : str) -> list:
        """for each module which needs to processed independently a task is created and described in a json file
        the format of the json file is analogous to that proposed in 
        https://root.cern/doc/master/classROOT_1_1RDF_1_1Experimental_1_1RDatasetSpec.html
        """
        
        task_list = []
        
        flist = glob.glob(nanodir+"/NANO*root")
        modules = self.getModulesFromRun(flist[0])

        #call the derived class implementation of the method to build the scan parameters
        scanparams_dict = self.buildScanParametersDict(flist,list(modules.keys()))

        #with all the information create a task per module
        for m,(fed,seq) in modules.items():
            
            task_spec={'samples':{}}
            for i,f in enumerate(flist):
                key=f'data{i+1}'
                task_spec['samples'][key] = {
                    'trees' : ['Events'],
                    'files' : [ self.xrootdFileName(f) ],
                    'metadata' : {'index':i+1, 'typecode':m, 'category':'data', 'fed':fed, 'seq':seq }
                }

                # add extra scan parameters (if any)
                extra_params = scanparams_dict[m][i]
                for k,v in extra_params.items():
                    task_spec['samples'][key]['metadata'][k]=v

            #save json 
            outjson=f"{self.output}/histofiller/{m}.json"
            with open(outjson, "w") as fout: 
                json.dump(task_spec, fout,  indent = 4)
            task_list.append( (self.output + '/histofiller', m, outjson) )

        #return the location of the tasks
        return task_list

    def getModulesFromRun(self, f : str) -> dict:
        """reads the run tree and builds a dict of {typecode: (fedId,Seq), ...} """

        modules_dict = {}
        runs = ROOT.RDataFrame("Runs",f).AsNumpy()
        for k,v in runs.items():

            #select typecode branches
            if k.find('HGCTypeCodes')!=0 : continue
            module_typecode = k.replace('HGCTypeCodes_','')

            #skip if the module is not required
            if len(self.moduleList)>0 and not module_typecode in self.moduleList:
                continue
                        
            #save the required information
            module_idx = v[0][0]
            module_fed = runs['HGCReadout_FED'][0][module_idx]
            module_seq = runs['HGCReadout_Seq'][0][module_idx]
            modules_dict[module_typecode] = (module_fed,module_seq)
             
        return modules_dict
    
    @staticmethod
    def xrootdFileName(f):    
        '''prepends the xrootd string to the file name'''

        if f.find('/eos/user')==0:
            return 'root://eosuser.cern.ch/'+f
        elif f.find('/eos/cms')==0:
            return 'root://eoscms.cern.ch/'+f
        return f

    @staticmethod
    def pdg_id(self, particle_name):
        '''Method to return the Particle ID following the PDG nomenclature'''
        if particle_name=='e': pdgId=11
        if particle_name=='mu': pdgId=13
        if particle_name=='pi': pdgId=211
        else: pdgId=0
        return pdgId        
