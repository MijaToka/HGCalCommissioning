import pandas as pd
import re
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
from HGCALCalibTaskWrapper import submitWrappedTasks
try:
  from HGCalCommissioning.LocalCalibration.JSONEncoder import *
except ImportError:
  sys.path.append('./python/')
  from JSONEncoder import *

  
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
 
    def __init__ (self,raw_args=None):
        """Constructor of HGCALCalibration class"""

        #parse arguments and add as class attributes
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-i", "--input", nargs='+',
                                 help='input directory=%(default)s',
                                 default="/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/Test/Run1743170957/c7e3e9cc-0cbd-11f0-8349-b8ca3af74182/prompt")
        self.parser.add_argument("-o", "--output",
                                help='output directory default=%(default)s',
                                default='./calibrations')
        self.parser.add_argument("--scanmap", metavar='JSON', default=None,
                                 help=("JSON file mapping a scan : run, directory and config parameters to use with their value"))
        self.parser.add_argument("--moduleList",
                                help='process only these modules (csv list) %(default)s',
                                default='', type=str)
        self.parser.add_argument("--task_spec",
                                 help='process a previously created task_spec',
                                 default=None, type=str)
        self.parser.add_argument("--maxThreads", type=int,
                                help='max threads to use=%(default)s',
                                default=8)
        self.parser.add_argument("--forceRewrite",
                                help='force re-write of previous output=%(default)s',
                                action='store_true')
        self.parser.add_argument("--skipHistoFiller",
                                 help='skip filling of the histograms=%(default)s',
                                 action='store_true')
        self.parser.add_argument("-v", '--verbosity', type=int, nargs='?', const=1, default=0,
                                 help="set verbosity level" )
        self.parser.add_argument("--doHexPlots",
                                 action='store_true',
                                 help='save hexplots')
        self.parser.add_argument("--createHistoFillerTask", action='store_true',
                                 help="Create task specs but do not execute anything else")
        self.parser.add_argument("--nosub", action='store_true', help="do not submit the histo filler task to condor (dry run)")
        self.addCommandLineOptions(self.parser)
        self.cmdargs = self.parser.parse_args(raw_args)

        #build the list of runs to analyze
        scanmap = {}
        if not self.cmdargs.scanmap is None:
            with open(self.cmdargs.scanmap,'r') as mapfile:
                scanmap = json.load(mapfile)
        else:
            scanmap["inc"] = { 'idx':0, 'input': [], 'params':{} }
            for i in self.cmdargs.input:
                scanmap['inc']['input'] += glob.glob(f'{i}/NANO*.root')
            
        #histogram filling
        calibresults = []
        if not self.cmdargs.skipHistoFiller:

            #check if upper class has defined an histogram filler
            if not hasattr(self, 'histofiller'):
                print('Setting base histogram filler has an attribute')
                self.histofiller = analyzeSimplePedestal

            #prepare the jobs (run info#modules, sub-samples, etc.)
            self.prepareHistogramFiller(scanmap)

            if self.cmdargs.createHistoFillerTask:
                submitWrappedTasks(tasks=self.histofill_tasks, classname=type(self).__name__, dryRun=self.cmdargs.nosub)
                return
                
            #launch tasks and fill rootfiles
            if self.cmdargs.maxThreads<=1: # sequential
                for task in self.histofill_tasks:
                  calibresults.append(self.histofiller(task))
            else: # multiprocess
                with Pool(self.cmdargs.maxThreads) as p:
                    calibresults = p.map(self.histofiller, self.histofill_tasks)
            print(f'Histo filling produced the following results {calibresults}')
        else:
            for url in glob.glob(f'{self.cmdargs.output}/histofiller/*.root'):
                typecode = re.findall('(.*).root',os.path.basename(url))[0]
                calibresults.append( (typecode,url) )
            print(f'Found the following results {calibresults}')
            
        #analysis of histograms will proceed only if not executing pre-filled task_specs
        #in that case the execution was probably carried by task splitting and needs to be hadded
        if not self.cmdargs.task_spec is None:
            print('As results of pre-filled task_specs are probably executed in chunks in HTCondor will stop here')
            print('Please hadd the Chunks and re-run with --skipHistoFiller option')
            return

        #analyze histogras
        tasklist = [ (typecode, url, self.cmdargs) for (typecode,url) in calibresults ]
        with Pool(self.cmdargs.maxThreads) as p:
            results = p.map(self.analyze, tasklist)            

        #create the corrections based on the analysis results
        jsonurl = self.createCorrectionsFile(results)
        print(f'Corrections stored in {jsonurl}')


    @abstractmethod
    def addCommandLineOptions(parser : argparse.ArgumentParser):
        pass


    @staticmethod
    @abstractmethod
    def analyze(args):
        pass


    @abstractmethod
    def createCorrectionsFile(results : list) -> str:
        pass


    def prepareHistogramFiller(self, scanmap : dict):
        """
        Steers preparation of the analysis for a run
        scanmap : dict = { 'key' : str : { 'idx' : int, 'input' : list of NANO, 'params' :dict }
        """

        #if a task spec is given use it directly
        if not self.cmdargs.task_spec is None:
            print('Using already existing task_spec')
            os.makedirs(self.cmdargs.output, exist_ok=True)
            self.histofill_tasks = [ (self.cmdargs.output, self.cmdargs.moduleList, self.cmdargs.task_spec, self.cmdargs), ]
            return

        #if not go through the whole procedure
        #prepare output
        if os.path.isdir(self.cmdargs.output) and not self.cmdargs.forceRewrite:
            raise ValueError(f'Output directory {self.cmdargs.output} already exists')        
        os.makedirs(self.cmdargs.output + '/histofiller', exist_ok=True)
        
        #create tasks
        self.histofill_tasks = self.buildHistoFillerTasks(scanmap)
        
    def buildScanParametersDict(self, file_list : list, module_list : list, nano_patt : str = 'Run(\d+)/(.*)/(.*)/NANO_(\d+)_(\d+).root') -> dict:
        """
        If the user passes a JSON via command line option --runmap, this default implementation will use
        it as a map between files/relays/runs and configuration parameters in order to define a dictionary
        of scan parameters that will be added to the metadata in buildHistoFillerTasks.
        Return lists of scanned parameters.
        """

        #read relay map
        if self.cmdargs.scanmap is None:
            return { }
        with open(self.cmdargs.scanmap,'r') as mapfile:
          scanmap = json.load(mapfile)


        #build the sequential list of scan parameters
        scanparams_list = []
        for i, fname in enumerate(file_list):

            try:
                run, uuid, version, run, lumi = re.findall(nano_patt,fname)[0]
            except Exception as e:
                print(f'WARNING! Failed to interpret nano patter in {fname} : {e}')
                continue
            
            if not run in scanmap:
                print(f'WARNING! Run {run} is not in the scanmap - available: {scanmap.keys()} - ignoring')
                continue

            scanparams = { }
            for mod in module_list:  # TODO: add module layer to scanmap ?
                scanparams[mod] = { 'index': i } # index of this scanpoint/run
                scanparams[mod].update(scanmap[run]) # { parameter: value }

            scanparams_list.append( scanparams )
            
        return scanparams_list


    def buildHistoFillerTasks(self, scanmap : dict) -> list:
        """for each module which needs to processed independently a task is created and described in a json file
        the format of the json file is analogous to that proposed in 
        https://root.cern/doc/master/classROOT_1_1RDF_1_1Experimental_1_1RDatasetSpec.html
        it returns a list of tuples containing the following information
        (outputdirectory, module name, json used to define the RDataFrame,commandline arguments)
        """

        task_list = []

        #get modules
        first_key = list(scanmap.keys())[0]
        first_file = scanmap[first_key]['input'][0]
        modules = self.getModulesFromRun(first_file)

        #with all the information create a task per module
        for m, (fed,seq,nerx) in modules.items():

            task_spec={'samples':{}}
            
            for scan_key, scan_point in scanmap.items():
                i = scan_point['idx']+1
                task_key = f'data{i}'
                task_spec['samples'][task_key] = {
                    'trees' : ['Events'],
                    'files' : [ self.xrootdFileName(f) for f in scan_point['input'] ],
                    'metadata' : {
                        'index':i,
                        'typecode':m,
                        'category':'data',
                        'fed':fed,
                        'seq':seq,
                        'nerx':nerx,
                        'type':type(self).__name__,
                        **scan_point['params']
                    }
                }

            #save json 
            outjson = f"{self.cmdargs.output}/histofiller/{m}.json"
            saveAsJson(outjson,task_spec)
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
