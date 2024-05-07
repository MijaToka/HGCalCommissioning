import pandas as pd
import glob
class HGCALCalibration():
    
    #Constructor of HGCALCalibration class
    def __init__ (self):
        pass
    
    #Method to return the Particle ID following the PDG nomenclature
    def pdg_id(self, particle_name):
        if particle_name=='e': pdgId=11
        if particle_name=='mu': pdgId=13
        if particle_name=='pi': pdgId=211
        else: pdgId=0

        return pdgId
        
    #Method to open a run registry, print info of the run and return the list of NANOAOD files available  
    def getNANOFiles(self, run, tbdir, maxFiles):
    
        #Open the run registry csv file
        run_registry = pd.read_csv(f'{tbdir}/runregistry.csv',sep='\s+', header='infer')
        #Read the run number
        row = run_registry[ run_registry['Run']==run ].iloc[0]
        #Read the output directory
        outdir = row['OutDir']
        #Find list of files in the outdir
        flist = glob.glob(outdir+"/*NANO*root")
        #Creates a vector with the number of files to count them
        if maxFiles>0:
          flist=flist[0:maxFiles]
          
        #Prints  
        print(f"Selected run {run} total events: {row['TotalEvents']}")
        print(f"Beam: {row['Beam']} Beam energy: {row['BeamEnergy']}")
        print(f"Shifter comments: {row['Description']}")
        print(f"Found {len(flist)} NANO fragments to process")
        
        #Return info from run.
        return {'run':run,
                'energy':(row['BeamEnergy'] if (row['BeamEnergy']!='None') else 0),
                'pdgId':self.pdg_id(row['Beam']),
                'files':flist}
    
               
    
    pass
