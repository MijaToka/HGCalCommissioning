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
        self.parser.add_argument("--task_spec",
                                 help='process a previously created task_spec',
                                 default=None, type=str)
        self.parser.add_argument("-r", "--relays", type=int, nargs='+',
                                help='single (or a list of) relay(s) =%(default)s',
                                default=None)
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
        self.parser.add_argument("--relaymap",metavar='JSON',
                                 help=("JSON file mapping relay number to a dictionary with extra"
                                       " config parameters and their value (e.g. for scan)"))
        self.parser.add_argument("--nanoTag",
                                 help='nano version tag to use, if empty use latest default=%(default)s',
                                 default='', type=str)
        self.parser.add_argument("-v", '--verbosity', type=int, nargs='?', const=1, default=0,
                                 help="set verbosity level" )
        self.parser.add_argument("--doHexPlots",
                                 action='store_true',
                                 help='save hexplots')
        self.parser.add_argument("--createHistoFillerTask", action='store_true',
                                 help="Create task specs but do not execute anything else")
        self.parser.add_argument("--nosub", action='store_true', help="do not submit the histo filler task to condor (dry run)")
        self.addCommandLineOptions(self.parser)
        self.cmdargs = self.parser.parse_args()

        #parse runs
        if self.cmdargs.relays is None:
            if self.cmdargs.relaymap:
                with open(self.cmdargs.relaymap,'r') as mapfile:
                    relaymap = json.load(mapfile)
                self.cmdargs.relays = [int(r) for r in relaymap]
                if self.cmdargs.verbosity>=1:
                    print(f"__init__: relays from relaymap {self.cmdargs.relays}")
            else:
                raise OSError("No runs defined via --run, nor --runmap !?")

        #run will always be appended to the output directory
        #except if we are executing and already pre-filled task spec
        if self.cmdargs.task_spec is None:
            if len(self.cmdargs.relays)==1: # single run (for pedestals, etc.)
                self.cmdargs.output=os.path.join(self.cmdargs.output,f'Relay{self.cmdargs.relays[0]}')
            else:
                self.cmdargs.output = os.path.join(self.cmdargs.output,f"Relay{self.cmdargs.relays[0]}-{self.cmdargs.relays[-1]}")

        #histogram filling
        calibresults = []
        if not self.cmdargs.skipHistoFiller:

            #check if upper class has defined an histogram filler
            if not hasattr(self, 'histofiller'):
                print('Setting base histogram filler has an attribute')
                self.histofiller = analyzeSimplePedestal

            #prepare the jobs (run info#modules, sub-samples, etc.)
            self.prepareHistogramFiller(self.cmdargs.nanoTag)

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


    def prepareHistogramFiller(self, nanotag : str):
        """
        Steers preparation of the analysis for a run (parse commandline,
        get run information, prepare output).
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

        #get the run row in the run registry
        try:
            nanodirs = self.getNANOFromRunRegistry(nanotag)
        except Exception as e:
            print(f'Failed to get info from run registry: {e}')
            print(f'Fallback on searching directory')
            print(f'Search for NANOS in : {self.cmdargs.input}/Relay{{{self.cmdargs.relays}}}')
            nanodirs = self.findNANOFrom(rdirlist = [f'{self.cmdargs.input}/Relay{r}' for r in self.cmdargs.relays], nanotag=nanotag )

        #create tasks
        self.histofill_tasks = self.buildHistoFillerTasks(nanodirs)


    def findNANOFrom(self, rdirlist : list, nanotag : str = ''):
        """looks for NANO files and pick the latest"""

        nanodirs = [ ]
        for d in rdirlist:
            nano  = f"{d}/*/*/NANO*.root"
            nanos = glob.glob(nano)

            #fall back on old scheme... this should go once run registry is compliant with new scheme
            if len(nanos)==0:
                rbasedir, run = re.findall('(.*)/Relay(\d+)', d)[0]
                nano  = f"{rbasedir}/Relay*/*/*/NANO_{run}_*.root"
                print(f'[findNANOFrom] fallback search with nano  = {nano} ... this make take longer')
                nanos += glob.glob(nano)
                
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
                print(f"WARNING! Could not find {nano}!")
                nanodirs.append(None)
            else:
                nanodirs.append(nano_versions.pop()[0])

        #check that at least one was found
        nmissed = sum([x is None for x in nanodirs])
        if nmissed>0:
            print(f"WARNING! {nmissed} directories have no NANO...")
            if nmissed == len(rdirlist):
                raise ValueError(f"No NANO to analyze...")

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
        try:
            if len(self.cmdargs.relays)==1:
                mask = (run_registry['Relay']==self.cmdargs.relay[0]) & (run_registry['RecoValid']==True)
            else: # for scans with multiple runs
                mask = (run_registry['Relay'].isin(self.cmdargs.relays)) & (run_registry['RecoValid']==True)
        except Exception as e:
            raise ValueError(f'Unable to find  {self.cmdargs.relay} in run registry file {e}')
        if mask.sum()==0:
            raise ValueError(f'Unable to find {self.cmdargs.relay} in run registry file')

        #look for NANO in the latest UUID
        return self.findNANOFrom(rdirlist = [run_registry.loc[mask].iloc[-1].copy()], nanotag = nanotag)


    def buildScanParametersDict(self, file_list : list, module_list : list, nano_patt : str = 'Relay(\d+)/(.*)/(.*)/NANO_(\d+)_(\d+).root') -> dict:
        """
        If the user passes a JSON via command line option --runmap, this default implementation will use
        it as a map between files/relays/runs and configuration parameters in order to define a dictionary
        of scan parameters that will be added to the metadata in buildHistoFillerTasks.
        Return lists of scanned parameters.
        """

        #read relay map
        if not self.cmdargs.relaymap:
            return { }
        with open(self.cmdargs.relaymap,'r') as mapfile:
          relaymap = json.load(mapfile)


        #build the sequential list of scan parameters
        scanparams_list = []
        for i, fname in enumerate(file_list):

            try:
                relay, uuid, version, run, lumi = re.findall(nano_patt,fname)[0]
            except Exception as e:
                print(f'WARNING! Failed to interpret nano patter in {fname} : {e}')
                continue
            
            if not relay in relaymap:
                print(f'WARNING! Relay {relay} is not in the relaymap - available: {relaymap.keys()} - ignoring')
                continue

            scanparams = { }
            for mod in module_list:  # TODO: add module layer to relaymap ?
                scanparams[mod] = { 'index': i } # index of this scanpoint/run
                scanparams[mod].update(relaymap[relay]) # { parameter: value }

            scanparams_list.append( scanparams )
            
        return scanparams_list


    def buildHistoFillerTasks(self, nanodirs : list) -> list:
        """for each module which needs to processed independently a task is created and described in a json file
        the format of the json file is analogous to that proposed in 
        https://root.cern/doc/master/classROOT_1_1RDF_1_1Experimental_1_1RDatasetSpec.html
        it returns a list of tuples containing the following information
        (outputdirectory, module name, json used to define the RDataFrame,commandline arguments)
        """

        task_list = []

        #create list of file lists
        flist = [ ]
        for nanodir in sorted(nanodirs):
            flist_ = glob.glob(f"{nanodir}/NANO*root")
            flist.extend(flist_)
            if self.cmdargs.verbosity>=1:
                print(f"buildHistoFillerTasks: nanodir={nanodir}: flist={flist_}")

        #get modules
        modules = self.getModulesFromRun(flist[0])

        #call the derived class implementation of the method to build the scan parameters
        scanparams_dict = self.buildScanParametersDict(flist,list(modules.keys()))

        #with all the information create a task per module
        for m, (fed,seq,nerx) in modules.items():

            task_spec={'samples':{}}
            for i, f in enumerate(flist):
                key=f'data{i+1}'
                task_spec['samples'][key] = {
                    'trees' : ['Events'],
                    'files' : [ self.xrootdFileName(f) ],
                    'metadata' : { 'index':i+1, 'typecode':m, 'category':'data', 'fed':fed, 'seq':seq, 'nerx':nerx, 'type':type(self).__name__}
                }

                #add extra scan parameters to metadata (if any)
                if len(scanparams_dict)>0:
                  extra_params = scanparams_dict[i][m]
                  task_spec['samples'][key]['metadata'].update(extra_params)

            #save json 
            outjson = f"{self.cmdargs.output}/histofiller/{m}.json"
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
