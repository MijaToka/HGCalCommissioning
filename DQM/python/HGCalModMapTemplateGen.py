from ROOT import TFile,TTree,TGraph
import pandas as pd
import numpy as np
import os

if 'CMSSW_BASE' not in os.environ:
    raise RuntimeError("CMSSW environment not set. Please run 'cmsenv' first.")

cmssw_base = os.environ['CMSSW_BASE']
hgcal_comm = 'src/HGCalCommissioning'
module_map = 'Configuration/data/ModuleMaps'
in_file = 'geometry.16.5.txt'

in_dir = os.path.join(cmssw_base,hgcal_comm,module_map,in_file)
print(in_dir)
dqm_data  = 'DQM/data'
out_file = 'geometry_v16.5.root'

out_dir = os.path.join(cmssw_base,hgcal_comm,dqm_data,out_file)
print(out_dir)


## Open the ModMap file and the output file
modMap = pd.read_csv(in_dir,sep=' ')

fout = TFile(out_dir,"RECREATE")

#Fill the root file
for module in modMap.itertuples():
    fout.mkdir(f"isSiPM_{module.isSiPM}/plane_{module.plane}/u_{module.u}/v_{module.v}")
    fout.cd(f"/isSiPM_{module.isSiPM}/plane_{module.plane}/u_{module.u}/v_{module.v}")

    x = np.array([getattr(module,"vx_{}".format(i)) for i in range(7)],dtype=float)/10
    y = np.array([getattr(module,"vy_{}".format(i)) for i in range(7)],dtype=float)/10
    
    graph = TGraph(module.nvertices+1, x, y)
    graph.SetTitle("")
    graph.SetName("module_bin")
    graph.GetXaxis().SetTitle("x [cm]")
    graph.GetYaxis().SetTitle("y [cm]")

    x0 = np.zeros(1,dtype=float)
    y0 = np.zeros(1,dtype=float)
    icassette = np.zeros(1,dtype=int)
    
    tree = TTree("module_properties","Module properties x0,y0,icassette")
    tree.Branch('x0',x0,'x0/D')
    tree.Branch('y0',y0,'y0/D')
    tree.Branch('icassette',icassette,'icassette/I')

    x0[0] = module.x0/10 #Modmap is in [mm] and the wafer maps are in [cm]
    y0[0] = module.y0/10
    icassette[0]= module.icassette

    tree.Fill()
    #center_position = ROOT.TVector2(module.x0/10,module.y0/10)

    graph.Write()
    tree.Write()
    #center_position.Write("module_x0y0")
    tree.SetDirectory(0)  # Detach so it's not written again
    del tree  # Cleanup reference

fout.Write()
fout.Close()




