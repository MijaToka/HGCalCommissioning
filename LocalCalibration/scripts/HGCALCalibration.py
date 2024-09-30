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
from DigiAnalysisUtils import analyzeSimplePedestal

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
                                 default='', type=str)
        self.addCommandLineOptions(self.parser)
        self.cmdargs = self.parser.parse_args()

        #run will always be appended to the output directory
        self.cmdargs.output=f'{self.cmdargs.output}/Run{self.cmdargs.run}'
        
        #histogram filling
        if not self.cmdargs.skipHistoFiller:

            #check if upper class has defined an histogram filler
            if not hasattr(self, 'histofiller'):
                print('Setting base histogram filler has an attribute')
                setattr(self,'histofiller',analyzeSimplePedestal)

            #prepare the jobs (run info#modules, sub-samples, etc.)
            self.prepareHistogramFiller(self.cmdargs.nanoTag)

            #launch tasks
            ntasks=len(self.histofill_tasks)        
            with Pool(self.cmdargs.maxThreads) as p:
                task_results=p.map(getattr(self,'histofiller'), self.histofill_tasks)
            print('Histo filling',task_results)

        #analysis of histograms
        rootfiles = glob.glob(f'{self.cmdargs.output}/histofiller/*.root')
        tasklist = [ (os.path.splitext(os.path.basename(url))[0], url, self.cmdargs) for url in rootfiles ]
        with Pool(self.cmdargs.maxThreads) as p:
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
        os.makedirs(self.cmdargs.output + '/histofiller', exist_ok=self.cmdargs.forceRewrite)

        #get the run row in the run registry
        try:
            nanodir = self.getNANOFromRunRegistry(nanotag)
        except Exception as e:
            print(f'Failed to get info from run registry: {e}')
            print(f'Fallback on searching directory')
            nanodir = self.findNANOFrom(rdirlist = [f'{self.cmdargs.input}/Run{self.cmdargs.run}'], nanotag=nanotag )

        #create tasks
        self.histofill_tasks = self.buildHistoFillerTasks(nanodir)
        
        return nanodir


    def findNANOFrom(self, rdirlist : list, nanotag : str = ''):
        """looks for NANO files and pick the latest"""

        nanodirs = []
        for d in rdirlist:
            nanos = glob.glob(f'{d}/*/*/NANO*.root')
            nano_versions=[]
            for n in nanos:
                ndir = os.path.dirname(n)
                nversion = os.path.basename(ndir)
                creation_time=os.path.getctime(ndir)

                #if a specific version is requested check it matches
                if nanotag!='' and nversion!=nanotag: continue
                nano_versions.append( (ndir,creation_time) )            
            nano_versions = sorted( list(set(nano_versions)), key=lambda x: x[1], reverse=False)

            if len(nano_versions)==0:
                nanodirs.append(None)
            else:
                nanodirs.append(nano_versions.pop()[0])

        #check that at least one was found
        nmissed = sum([x is None for x in nanodirs])
        if nmissed>0:
            print(f'{nmissed} directories have no NANO...')
            if nmissed == len(rdirlist):
                raise ValueError(f'No NANO to analyze...')

        return [x for x in nanodirs if not x is None]
    
        
    def getNANOFromRunRegistry(self, nanotag : str) -> pd.core.series.Series:
        """reads the run registry and retrieves the information about this run"""

        #check if run registry is valid and open it
        runregfiles = glob.glob(f'{self.cmdargs.input}/runregistry*')
        if len(runregfiles)==0:
            raise OSError(f"No runregistry files in {self.cmdargs.input}")
        _, runreg_ext = os.path.splitext(runregfiles[0])
        if runreg_ext=='.csv':
            run_registry = pd.read_csv(runregfiles[0],sep='\s+', header='infer')
        elif runreg_ext=='.feather':
            run_registry = pd.read_feather(runregfiles[0])
        else:
            raise IOError(f'Unable to decode runregistry with {runreg_ext} extension')
        
        #get the run
        mask = (run_registry['Run']==self.cmdargs.run) & (run_registry['RecoValid']==True)
        if mask.sum()==0:
            raise ValueError(f'Unable to find {self.cmdargs.run} in run registry file')

        #look for NANO in the latest UUID
        return self.findNANOFrom(rdirlist = [run_registry.loc[mask].iloc[-1].copy()], nanotag = nanotag)


    def buildHistoFillerTasks(self, nanodir : list) -> list:
        """for each module which needs to processed independently a task is created and described in a json file
        the format of the json file is analogous to that proposed in 
        https://root.cern/doc/master/classROOT_1_1RDF_1_1Experimental_1_1RDatasetSpec.html
        it returns a list of tuples containing the following information
        (outputdirectory, module name, json used to define the RDataFrame,commandline arguments)
        """
        
        task_list = []

        #FIXME this may be a list now
        flist = glob.glob(f'{nanodir[0]}/NANO*root')
        flist = sorted(flist)
        modules = self.getModulesFromRun(flist[0])

        #call the derived class implementation of the method to build the scan parameters
        scanparams_dict = self.buildScanParametersDict(flist,list(modules.keys()))

        #with all the information create a task per module
        for m,(fed,seq,nerx) in modules.items():
            
            task_spec={'samples':{}}
            for i,f in enumerate(flist):
                key=f'data{i+1}'
                task_spec['samples'][key] = {
                    'trees' : ['Events'],
                    'files' : [ self.xrootdFileName(f) ],
                    'metadata' : {'index':i+1, 'typecode':m, 'category':'data', 'fed':fed, 'seq':seq, 'nerx':nerx }
                }

                # add extra scan parameters (if any)
                extra_params = scanparams_dict[m][i]
                for k,v in extra_params.items():
                    task_spec['samples'][key]['metadata'][k]=v

            #save json 
            outjson=f"{self.cmdargs.output}/histofiller/{m}.json"
            with open(outjson, "w") as fout: 
                json.dump(task_spec, fout,  indent = 4)
            task_list.append( (self.cmdargs.output + '/histofiller', m, outjson, self.cmdargs) )

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
            if len(self.cmdargs.moduleList)>0 and not module_typecode in self.cmdargs.moduleList:
                continue
                        
            #save the required information
            module_idx = v[0][0]
            module_fed = runs['HGCReadout_FED'][0][module_idx]
            module_seq = runs['HGCReadout_Seq'][0][module_idx]
            if 'HGCReadout_nErx' in runs:
                module_nerx = runs['HGCReadout_nErx'][0][module_idx]
            else:
                #remove once all NANO has this
                print(f'Using default nErx for {module_typecode}') 
                module_nerx =  6
            modules_dict[module_typecode] = (module_fed,module_seq,module_nerx)
             
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
