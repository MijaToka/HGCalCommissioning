#include "FWCore/MessageLogger/interface/MessageLogger.h"

#include <Eigen/Core>

#include <iostream>
#include <iomanip>
#include <stdio.h>
#include <string>
#include <sstream>
#include <math.h>
#include <map>

#include <chrono>
#include <ctime>

//Framework
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "FWCore/Framework/interface/ESWatcher.h"
#include "FWCore/ParameterSet/interface/FileInPath.h"

//DQM
#include "DQMServices/Core/interface/DQMEDHarvester.h"
#include "DQMServices/Core/interface/DQMStore.h"
#include "DQMServices/Core/interface/MonitorElement.h"

#include "HGCalCommissioning/DQM/interface/HGCalSysValDQMCommon.h"
#include "CondFormats/DataRecord/interface/HGCalElectronicsMappingRcd.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingModuleIndexer.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingParameterHost.h"

#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalModuleIndexerTrigger.h"

#include <TDatime.h>
#include <TString.h>
#include <TFile.h>
#include <TKey.h>
#include <TGraph.h>
#include <TPolyLine.h>
#include <TTree.h>

#include <fstream>
#include <iostream>

using namespace hgcal::dqm;

/**
   @short DQM harvester for the DIGI monitoring elements at the end of lumi section / run 
*/
class HGCalSysValDigisHarvester : public DQMEDHarvester {
public:
  typedef std::pair<unsigned int, unsigned int> ElecKey_t; // (fed-id, ECON-D index)
  typedef std::tuple<bool,int,int,int> GeomKey_t;

  HGCalSysValDigisHarvester(const edm::ParameterSet &ps);
  virtual ~HGCalSysValDigisHarvester();
  static void fillDescriptions(edm::ConfigurationDescriptions &descriptions);

protected:
  void beginJob();
  void dqmEndLuminosityBlock(DQMStore::IBooker &,
                             DQMStore::IGetter &,
                             edm::LuminosityBlock const &,
                             edm::EventSetup const &);
  void dqmDAQHexaPlots(DQMStore::IBooker &,
                       DQMStore::IGetter &,
                       edm::LuminosityBlock const &,
                       edm::EventSetup const &);
  void dqmTriggerHexaPlots(DQMStore::IBooker &,
                           DQMStore::IGetter &,
                           edm::LuminosityBlock const &,
                           edm::EventSetup const &);
  void dqmEndJob(DQMStore::IBooker &, DQMStore::IGetter &) override;

  std::map<TGraph*, double> extractBinLocations(TH2Poly* hist);

private:

  /**
    @short applies a counter-clockwise rotation in multiples of 60deg to a shape described by a TGraph
   */
  void rotateShape(TGraph *gr, char irot);
  /**
    @short applies a translation of the bin un the x-y plane
   */
  void translateBin(TGraph *gr,float x0, float y0);
/**
    @short retieves the TGraph found in /isSiPM_{isSiPM}/plane_{plane}/u_{u}/v_{v} from the geometry file
*/
  TGraph* getModuleBin(TFile* file, bool isSiPM,int plane,int u, int v);

/**
    @short retieves the x0,y0 position found in /isSiPM_{isSiPM}/plane_{plane}/u_{u}/v_{v} from the geometry file 
*/
  std::vector<double> getModuleCenter(TFile* file, bool isSiPM,int plane,int u, int v);

  //location of the hex map templates
  std::string templateDir_;

  //skip trigger plots
  bool skipTriggerHarvesting_;
    
  //module indexer / info
  edm::ESGetToken<HGCalMappingModuleIndexer, HGCalElectronicsMappingRcd> moduleIdxTkn_;
  edm::ESGetToken<hgcal::HGCalMappingModuleParamHost, HGCalElectronicsMappingRcd> moduleInfoTkn_;
  
  //monitoring elements
  MonitorElement *occupancyLayer_,*meTimestamp_;
  std::map<std::string, MonitorElement *> Module_;

  const std::string variables[8] = {"occupancy","avgcm","avgadc","stdadc","deltaadc","avgtoa","avgtot","n_dead_channels"};
  std::map<std::string,std::string> SummaryLabel {
    {"occupancy","Occupancy"},
    {"avgcm",getLabelForSummaryIndex(SummaryIndices_t::CMAVG)},
    {"avgadc",getLabelForSummaryIndex(SummaryIndices_t::PEDESTAL)},
    {"stdadc",getLabelForSummaryIndex(SummaryIndices_t::NOISE)},
    {"deltaadc",getLabelForSummaryIndex(SummaryIndices_t::DELTAPEDESTAL)},
    {"avgtoa",getLabelForSummaryIndex(SummaryIndices_t::TOAAVG)},
    {"avgtot",getLabelForSummaryIndex(SummaryIndices_t::TOTAVG)},
    {"n_dead_channels","Occupancy"}
  };

  const std::string geometryTemplate_ = "/geometry_v16.5.root";
  const std::string templateFile_ = "/ModuleMaps/geometry_B27_v5.root";


  //template information holders
  std::map<std::string, std::vector<double>> modules_centers;
  std::map<std::string, std::vector<std::vector<float>>> modules_corners;
  std::map<std::string,int> modules_nvertices;

  // layer/type/me
  std::map<unsigned int, std::map<std::string, MonitorElement *> > hexLayerAverage_;
  std::map<unsigned int, std::map<std::string, MonitorElement *> > hexLayerModule_;
  // module/type/me
  std::map<std::string, std::map<std::string, MonitorElement *> > hexPlots_;  

  HGCalModuleIndexerTrigger moduleIndexerTrigger_;
  std::vector<std::string> BXlist = {"BXm3", "BXm2", "BXm1", "BX0", "BXp1", "BXp2", "BXp3"};
  std::map<int, char> irotstates_trigger = {{0,0},{1,1},{2,2}};

};

//
HGCalSysValDigisHarvester::HGCalSysValDigisHarvester(const edm::ParameterSet &iConfig)
  : templateDir_(iConfig.getParameter<std::string>("TemplateFiles")),
    skipTriggerHarvesting_(iConfig.getParameter<bool>("SkipTriggerHarvesting")),
    moduleIdxTkn_(esConsumes<edm::Transition::EndLuminosityBlock>()),
    moduleInfoTkn_(esConsumes<edm::Transition::EndLuminosityBlock>())
{

}

//
void HGCalSysValDigisHarvester::fillDescriptions(edm::ConfigurationDescriptions &descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<std::string>("TemplateFiles","HGCalCommissioning/DQM/data");
  desc.add<bool>("SkipTriggerHarvesting",true);
  descriptions.addWithDefaultLabel(desc);
}

//
HGCalSysValDigisHarvester::~HGCalSysValDigisHarvester() { edm::LogInfo("HGCalSysValDigisHarvester") << "@ DTOR"; }

//
void HGCalSysValDigisHarvester::beginJob() { edm::LogInfo("HGCalSysValDigisHarvester") << " @ beginJob"; }

//
void HGCalSysValDigisHarvester::dqmEndLuminosityBlock(DQMStore::IBooker &ibooker,
                                                      DQMStore::IGetter &igetter,
                                                      edm::LuminosityBlock const &iLumi,
                                                      edm::EventSetup const &iSetup) {
   dqmDAQHexaPlots(ibooker, igetter, iLumi, iSetup);
   if(!skipTriggerHarvesting_)
     dqmTriggerHexaPlots(ibooker, igetter, iLumi, iSetup); 
}


void HGCalSysValDigisHarvester::dqmDAQHexaPlots(DQMStore::IBooker &ibooker,
                                                      DQMStore::IGetter &igetter,
                                                      edm::LuminosityBlock const &iLumi,
                                                      edm::EventSetup const &iSetup) {
  
  //read the available modules from the ECON-D payload histogram
  std::vector<std::string> typecodes;
  const MonitorElement *me = igetter.get("HGCAL/Digis/econdPayload");
  TAxis *xaxis = me->getTH2F()->GetXaxis();
  for(int i=1; i<=xaxis->GetNbins(); i++)
    typecodes.push_back( xaxis->GetBinLabel(i) );

  //get module indexer and module info to fill the rotation index of the modules
  //for a better display of the hexplots
  std::vector<char> irotstates(typecodes.size(),0);
  std::vector<int> layerstates(typecodes.size(),0),ustates(typecodes.size(),0),vstates(typecodes.size(),0);
  std::vector<bool> isSiPMstates(typecodes.size(),0);

  std::vector<std::vector<double>> x0y0states(typecodes.size(),std::vector<double>(2,0));
  std::vector<TGraph*> binstates(typecodes.size(),0);
  
  auto const& moduleIndexer = iSetup.getData(moduleIdxTkn_);
  auto const& moduleInfo = iSetup.getData(moduleInfoTkn_);
  for(auto it : moduleIndexer.getTypecodeMap()) {

    //dqmIndex as pre-determined in the DigisClient
    uint32_t fedid = it.second.first;
    uint32_t imod = it.second.second;
    uint32_t dqmIndex = moduleIndexer.getIndexForModule(fedid, imod);

    //module information
    auto modInfo = moduleInfo.view()[dqmIndex];
    irotstates[dqmIndex] = modInfo.irot();
    layerstates[dqmIndex] = modInfo.plane();

    std::string geometryFile = templateDir_+geometryTemplate_;
    edm::FileInPath fiptemp(geometryFile);
    TFile* file = TFile::Open(fiptemp.fullPath().c_str(), "READ");
    
    x0y0states[dqmIndex] = getModuleCenter(file, modInfo.isSiPM(),modInfo.plane(),modInfo.i1(),modInfo.i2());
    binstates[dqmIndex] = getModuleBin(file, modInfo.isSiPM(),modInfo.plane(),modInfo.i1(),modInfo.i2());

    file->Close();
  }

  //define layer-level summary
  ibooker.setCurrentFolder("HGCAL/Layers/Summary");
  size_t nLayers = 26; // NOTE: place holder for CE-E layers. Only two layers in 2024 beam test
  size_t nModules = typecodes.size();
  occupancyLayer_ = ibooker.book1D("summary_occupancy_layer", ";Layer; #hits", nLayers, 0.5, nLayers+0.5);
  
  std::map<std::string,float> value_module;
  
  float total_nHits_layer = 0; // M0, M1, M2 in layer1; M3, M4, M5 in layer2
    
  for (std::string variable: variables) {
    value_module[variable] = 0.;
    Module_[variable] = ibooker.book1D("summary_"+variable+"_module", ";Module; value", nModules, 0.5, nLayers+0.5);
  }
  
  ibooker.setCurrentFolder("HGCAL/Layers/");
  // Get current timestamp
  auto now = std::chrono::system_clock::now();
  std::time_t timestamp = std::chrono::system_clock::to_time_t(now);
  TDatime dt(timestamp);
  TString timeString = dt.AsSQLString();
  std::cout << "Timestamp as TString: " << timeString.Data() << std::endl;
  meTimestamp_ = ibooker.bookString("info_timestamp", timeString);

  //define the layer-dqm plots average and cell
  // nLayers = 1;
  for(int layer:layerstates){ // for each layer
    std::ostringstream ss, st;
    ss << "_layer_" << layer;
    st << "Layer_" << layer;
    std::string tag(ss.str());
    std::string title(st.str());
    //std::cout << layer << std::endl;
    //define layer-level module plots
    ibooker.setCurrentFolder("HGCAL/Layers/Layer_"+std::to_string(layer)+"/Average");
    for (std::string variable:variables) {
      hexLayerAverage_[layer][variable] = ibooker.book2DPoly("module_"+variable+tag,  title + "; x[cm]; y[cm];Occupancy",  13, 163.85, 2, 42);
    }
    //define layer-level  cell plots
    ibooker.setCurrentFolder("HGCAL/Layers/Layer_"+std::to_string(layer)+"/Hex");
    for (std::string variable:variables) {
      hexLayerModule_[layer][variable] = ibooker.book2DPoly("hex_"+variable+tag,  title + "; x[cm]; y[cm];"+SummaryLabel[variable], 13, 163.85, 2, 42);
    }
  }


  //book the hex summary plots
  ibooker.setCurrentFolder("HGCAL/Modules");

  std::map<int,uint32_t> iMod; //Per layer this is the index shift to plot correcly the hex plots
  for (int layer : layerstates) {
    iMod[layer] = 0;
  }

  for(size_t i=0; i<typecodes.size(); i++) { // for each module
    
    std::string t = typecodes[i];
    char irot = irotstates[i];
    int layer = layerstates[i];
    std::vector<double> x0y0 = x0y0states[i];
    
    double x0 = x0y0[0];
    double y0 = x0y0[1];

    //std::string modulename = t.c_str();

    //std::cout << "Module : "<<t.c_str()<<", x_0 : "<< x0 <<", y_0 : "<< y0<<std::endl;

    std::ostringstream ss;
    ss << "_module_" << i;
    std::string tag(ss.str());

    //set layer-level summary plots
    auto binlabel = t.c_str();
    
    for (std::string variable:variables){
      Module_[variable]->setBinLabel(i+1,binlabel,1);
    }

    //define the hex plots
    hexPlots_[t]["avgcm"]     = ibooker.book2DPoly("hex_avgcm"+tag,  t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::CMAVG), -14, 14, -14, 14);
    hexPlots_[t]["avgadc"]    = ibooker.book2DPoly("hex_avgadc"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::PEDESTAL), -14, 14, -14, 14);
    hexPlots_[t]["stdadc"]    = ibooker.book2DPoly("hex_stdadc"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::NOISE), -14, 14, -14, 14);
    hexPlots_[t]["deltaadc"]  = ibooker.book2DPoly("hex_deltaadc"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::DELTAPEDESTAL), -14, 14, -14, 14);
    hexPlots_[t]["avgtoa"]    = ibooker.book2DPoly("hex_avgtoa"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::TOAAVG), -14, 14, -14, 14);
    hexPlots_[t]["avgtot"]    = ibooker.book2DPoly("hex_avgtot"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::TOTAVG), -14, 14, -14, 14);
    hexPlots_[t]["occupancy"] = ibooker.book2DPoly("hex_occupancy"+tag, t + "; x[cm]; y[cm];Occupancy", -14, 14, -14, 14);

    //the sums histogram + helper functions to compute final quantities
    const MonitorElement *sum_me = igetter.get("HGCAL/Digis/sums" + tag);
    const MonitorElement *occ_me = igetter.get("HGCAL/Digis/occupancy" + tag);
    auto num = [](SumIndices_t nidx, uint32_t chIdx, const MonitorElement *sum_me) -> float {
      float n = sum_me->getBinContent(chIdx+1,nidx+1);
      return n;
    };
    auto mean = [](SumIndices_t vidx, SumIndices_t nidx, uint32_t chIdx, const MonitorElement *sum_me) -> float { 
      float n = sum_me->getBinContent(chIdx+1,nidx+1);
      float v = sum_me->getBinContent(chIdx+1,vidx+1);
      return n>0 ?  v/n : 0.f;
    };
    auto stddev = [](SumIndices_t vvidx, SumIndices_t vidx, SumIndices_t nidx,uint32_t chIdx, const MonitorElement *sum_me) -> float { 
      float n = sum_me->getBinContent(chIdx+1, nidx+1);
      float v = sum_me->getBinContent(chIdx+1, vidx+1);
      float vv = sum_me->getBinContent(chIdx+1, vvidx+1);
      float std = n > 1 ? (vv/n-pow(v/n,2))*(n/(n-1)) : 0.f;      
      return std<0 ? -sqrt(fabs(std)) : sqrt(std); // why does std become negative??
    };

    //open file and loop over keys to hadd to THPoly (sequence of channel representations)
    std::string geourl = templateDir_ + "/WaferMaps/geometry_" + t.substr(0,4) + "_wafer.root";
    edm::FileInPath fip(geourl);
    TFile *fgeo = new TFile(fip.fullPath().c_str(), "R");
    TKey *key;
    TIter nextkey(fgeo->GetDirectory(nullptr)->GetListOfKeys());
    uint32_t iobj(0);
    uint32_t deltaIdx(0);
    while ((key = (TKey *)nextkey())) { // for each cell

      TObject *obj = key->ReadObj();
      if (!obj->InheritsFrom("TGraph")) continue;
      TGraph *gr = (TGraph *)obj;

      //skip CM or NC channels
      bool isCM = (iobj % 39 == 37) || (iobj % 39 == 38);
      bool isNC = ((iobj % 39 == 8) || (iobj % 39 == 17) || (iobj % 39 == 19) || (iobj % 39 == 28)) 
                && t.substr(0,2) == "ML";
      if(isCM) {
        iobj++;
        continue;
      }
      if(isNC){
        deltaIdx++;
      }

      //apply rotation
      rotateShape(gr,irot);
      //rotateShape(grLayer,irot);
      
      //compute summary for this standard channel
      unsigned eRx = int(iobj/39); //NOTE: CM channels were included in the objects
      unsigned chIdx = iobj - eRx*2; //from the channel index subtract the 2 CM channels per roc

      float nHits = num(SumIndices_t::NADC, chIdx, sum_me) + num(SumIndices_t::NTOT, chIdx, sum_me);
      total_nHits_layer += nHits;
      value_module["occupancy"] += nHits;
      
      float avgcm = mean( SumIndices_t::SUMCM, SumIndices_t::NCM, chIdx, sum_me);
      hexPlots_[t]["avgcm"]->addBin(gr);
      hexPlots_[t]["avgcm"]->setBinContent(chIdx+1, avgcm); 
      value_module["avgcm"] += avgcm;     
      
      float avgadc = mean( SumIndices_t::SUMADC, SumIndices_t::NADC, chIdx, sum_me);
      hexPlots_[t]["avgadc"]->addBin(gr);
      hexPlots_[t]["avgadc"]->setBinContent(chIdx+1, avgadc);
      value_module["avgadc"] += avgadc;
      

      float stdadc = stddev( SumIndices_t::SUMADC2, SumIndices_t::SUMADC, SumIndices_t::NADC, chIdx, sum_me);
      hexPlots_[t]["stdadc"]->addBin(gr);
      hexPlots_[t]["stdadc"]->setBinContent(chIdx+1, stdadc);
      value_module["stdadc"] += stdadc;

      float deltaadc = avgadc - mean( SumIndices_t::SUMADCM1, SumIndices_t::NADCM1, chIdx, sum_me);
      hexPlots_[t]["deltaadc"]->addBin(gr);
      hexPlots_[t]["deltaadc"]->setBinContent(chIdx+1, deltaadc);
      value_module["deltaadc"] += deltaadc;

      float avgtoa = mean( SumIndices_t::SUMTOA, SumIndices_t::NTOA, chIdx, sum_me);
      hexPlots_[t]["avgtoa"]->addBin(gr);
      hexPlots_[t]["avgtoa"]->setBinContent(chIdx+1, avgtoa);
      value_module["avgtoa"]+=avgtoa;

      float avgtot = mean( SumIndices_t::SUMTOT, SumIndices_t::NTOT, chIdx, sum_me);
      hexPlots_[t]["avgtot"]->addBin(gr);
      hexPlots_[t]["avgtot"]->setBinContent(chIdx+1, avgtot);
      value_module["avgtot"]+=avgtot;

      float occval = occ_me->getBinContent(chIdx+1);
      hexPlots_[t]["occupancy"]->addBin(gr);
      hexPlots_[t]["occupancy"]->setBinContent(chIdx+1, occval);

      if (!isNC) {
      TGraph *grLayer = new TGraph(*static_cast<TGraph *>(gr));
      translateBin(grLayer,x0,y0); // The bins are already rotated
      
      /**
        iMod[layer]+chIdx-deltaIdx+1 is the index of the bin since we are skipping the CM and NC
        * iMod[Layer]: each layer has it's own counter that saves the index shift from having already filled an ammount full modules
        * chIdx = iobj-2*int(iobj/39) skippes the index of the CM channel that is counted in iobj.
        * deltaIdx is equivalent to the int(iobj/39) for CM but it gets increased each time we loop over a NC channel.
        (chIdx could be iobj-deltaIdxNC-deltaIdxCM with each one getting increased whenever we loop a NC or CM channel)
      */
      hexLayerModule_[layer]["avgcm"]->addBin(grLayer);
      hexLayerModule_[layer]["avgcm"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,avgcm);
      
      hexLayerModule_[layer]["avgadc"]->addBin(grLayer);
      hexLayerModule_[layer]["avgadc"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,avgadc);
      
      hexLayerModule_[layer]["n_dead_channels"]->addBin(grLayer);
      if (avgadc==0.){
        value_module["n_dead_channels"] += 1;
        hexLayerModule_[layer]["n_dead_channels"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,1);
      }
      hexLayerModule_[layer]["stdadc"]->addBin(grLayer);
      hexLayerModule_[layer]["stdadc"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,stdadc);

      hexLayerModule_[layer]["deltaadc"]->addBin(grLayer);
      hexLayerModule_[layer]["deltaadc"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,deltaadc);

      hexLayerModule_[layer]["avgtoa"]->addBin(grLayer);
      hexLayerModule_[layer]["avgtoa"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,avgtoa);

      hexLayerModule_[layer]["avgtot"]->addBin(grLayer);
      hexLayerModule_[layer]["avgtot"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,avgtot);

      hexLayerModule_[layer]["occupancy"]->addBin(grLayer);
      hexLayerModule_[layer]["occupancy"]->setBinContent(iMod[layer]+chIdx-deltaIdx+1,occval);
      }
      iobj++;
    }
    iMod[layer] +=iobj-2*int(iobj/39)-deltaIdx;

    char value = t.c_str()[1];
    int n_cells;
    int n_CM_cells;
   
   switch (value){
       case 'H':
       n_cells = 72*6;
       n_CM_cells = 12; //
       break;
       case 'L':
       n_cells = 72*3; //The NC cells are counted and averaged as well
       n_CM_cells = 6;
       break;
       default:
       n_cells = 1;
       n_CM_cells = 0;
       break;
   }
    
    for (std::string variable:variables){
      if (!(variable == "occupancy" || variable =="n_dead_channels")){
        value_module[variable] /= n_cells;
      }else if (variable =="n_dead_channels")
      {
        value_module[variable] -= n_CM_cells;
      }
        
      
      
    }//end loop over template file keys
    
    //close template file
    fgeo->Close();


    for (std::string variable:variables){
      Module_[variable]->setBinContent(i+1,value_module[variable]);
      value_module[variable] = 0;
    }

    //fill layer information


    if((i+1)%11==0) {
        occupancyLayer_->setBinContent((i+1)/11, total_nHits_layer);
        total_nHits_layer = 0.;
        //iLayer++;
    }
  //std::cout << "********** typecode = " << typecodes[i].c_str() <<'\n';
  }//end loop over typecodes of this run
  std::map<int,int> iLayer; //Per layer, index of the current Module bin in each layer as to plot correctly the average plot
  for (int layer:layerstates){
    iLayer[layer]=0;
  }
  //register layer-level geometry & fill bin contents
  for (size_t i=0;i<typecodes.size();i++){ //for each module
    std::string t = typecodes[i];
    //char irot = irotstates[i];
    int layer = layerstates[i];

    TGraph* gr = binstates[i];
    
    if (!gr){
      std::cerr << "Could not generate the bin."<<std::endl;
    }
    
    gr->SetName(t.c_str());

    for (std::string variable:variables) {
      value_module[variable] = Module_[variable]->getBinContent(i+1);
      //hexLayerAverage_[i][variable]->setBinLabel(layerModuleIdx+1,binlabel,1);
      hexLayerAverage_[layer][variable]->addBin(gr);
      hexLayerAverage_[layer][variable]->setBinContent(iLayer[layer]+1,value_module[variable]);
    }
    iLayer[layer]++;
  }
  edm::LogInfo("HGCalSysValDigisHarvester") << "Defined hex plots for " << typecodes.size();  
}


void HGCalSysValDigisHarvester::dqmTriggerHexaPlots(DQMStore::IBooker &ibooker,
                                                      DQMStore::IGetter &igetter,
                                                      edm::LuminosityBlock const &iLumi,
                                                      edm::EventSetup const &iSetup) {
  ibooker.setCurrentFolder("HGCAL/Modules");
  std::string typecode = "ML_F_TC";
  std::string digiDir = "HGCAL/Digis/";

  hexPlots_[typecode]["channel_test"] = ibooker.book2DPoly("hex_channel_test",  typecode + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::CMAVG), -150, 150, -150, 150);
  int nLayers = 1;
  int nModules = 11;
  for(auto BX : BXlist) {
    for(int layer = 0; layer < nLayers; layer++) {
      for(int module = 0; module < nModules; module++) {
        std::string module_energy_path = BX + "_energy_layer_" + std::to_string(layer) + "_module_" + std::to_string(module);
        hexPlots_[typecode][module_energy_path] = ibooker.book2DPoly(module_energy_path,  typecode + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::CMAVG), -150, 150, -150, 150);
        std::string module_location_path = BX + "_location_layer_" + std::to_string(layer) + "_module_" + std::to_string(module);
        hexPlots_[typecode][module_location_path] = ibooker.book2DPoly(module_location_path,  typecode + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::CMAVG), -150, 150, -150, 150);
      }
    }
  }

  std::string geourl = templateDir_ + "/geometry_" + typecode + "_wafer.root";  
  edm::FileInPath fip(geourl);
  TFile *fgeo = new TFile(fip.fullPath().c_str(), "R");
  
  TH2Poly *hex = (TH2Poly *)fgeo->Get("hex");

  std::map<TGraph*, double> hexPlots = extractBinLocations(hex);

  int i = 0;
  for (auto const& [polygon, channel] : hexPlots) {

    hexPlots_[typecode]["channel_test"]->addBin(polygon);
    hexPlots_[typecode]["channel_test"]->setBinContent(i+1, channel);


    for(auto BX : BXlist) {
      for(int layer = 0; layer < nLayers; layer++) {
        for(int module = 0; module < nModules; module++) {

          std::string module_energy_path = BX + "_energy_layer_" + std::to_string(layer) + "_module_" + std::to_string(module);
          std::string channel_energy_path = digiDir + module_energy_path + "_channel_" + std::to_string(static_cast<int>(channel));
          const MonitorElement *energy_element = igetter.get(channel_energy_path);
          if (!energy_element) {
            std::cerr << "Error: Could not find MonitorElement for " << channel_energy_path << std::endl;
            continue;
          }
          const TH1F* energy_hist = energy_element->getTH1F();
          double energy = 0;
          if (energy_hist) { energy = energy_hist->GetMean(); }

          // make a deep copy of the polygon
          auto polygon_ = new TGraph(*polygon);
          //char irot = irotstates_trigger[module];
          // rotateShape(polygon_,irot);

          hexPlots_[typecode][module_energy_path]->addBin(polygon_);
          hexPlots_[typecode][module_energy_path]->setBinContent(i+1, energy);

          std::string module_location_path = BX + "_location_layer_" + std::to_string(layer) + "_module_" + std::to_string(module);
          std::string channel_location_path = digiDir + module_location_path + "_channel_" + std::to_string(static_cast<int>(channel));
          const MonitorElement *location_element = igetter.get(channel_location_path);
          if (!location_element) {
            std::cerr << "Error: Could not find MonitorElement for " << channel_location_path << std::endl;
            continue;
          }
          const TH1F* location_hist = location_element->getTH1F();
          double location = 0;
          if (location_hist) { location = location_hist->GetMean(); }
          hexPlots_[typecode][module_location_path]->addBin(polygon);
          hexPlots_[typecode][module_location_path]->setBinContent(i+1, location);
        }
      }
    }

    i++;
  }

  fgeo->Close();

}

std::map<TGraph*, double> HGCalSysValDigisHarvester::extractBinLocations(TH2Poly* hist) {
  // Get the list of bins from the TH2Poly
  
  std::map<TGraph*, double> hexPlots;
  TList* bins = hist->GetBins();
  if (!bins) {
    std::cout << "No bins found in the TH2Poly." << std::endl;
    return hexPlots;
  }

  // Loop over all bins
  for (int i = 0; i < bins->GetSize(); ++i) {
    // Get the current bin as a TPolyLine
    TH2PolyBin* bin = dynamic_cast<TH2PolyBin*>(bins->At(i));

    double channel = hist->GetBinContent(i+1);

    if (bin) {
      // Get the number of vertices in the bin
      TGraph* polygon = dynamic_cast<TGraph*>(bin->GetPolygon());

      hexPlots[polygon] = channel;
    } else {
      std::cout << "Error: Bin " << i << " is not a valid TPolyLine." << std::endl;
    }
  }
  return hexPlots;
}


//
void HGCalSysValDigisHarvester::rotateShape(TGraph *gr, char irot) {

  //define the full rotation matrix
  //the template needs a 150 deg shift to be put in the standard position 
  //the template is rotated by -90° not 150° (?)
  float angle(irot*M_PI/3.-M_PI/2.);
  Eigen::Matrix2d rotationMatrix;
  rotationMatrix <<
    std::cos(angle), -std::sin(angle),
    std::sin(angle),  std::cos(angle);

  //apply matrix on each pair of coordinates and change the graph points
  for(int i=0; i<gr->GetN(); i++) {

    Eigen::Vector2d vec(gr->GetX()[i],gr->GetY()[i]); 
    Eigen::Vector2d rvec = rotationMatrix * vec;

    gr->SetPoint(i,rvec.x(),rvec.y());
  }
  
}


void HGCalSysValDigisHarvester::translateBin(TGraph *gr, float x0, float y0) {
  
  //Translates all the cells of the module so that it's centered at (x0,y0) 
  for (int i=0; i<gr->GetN();i++) {

    float translated_x = gr->GetX()[i] + x0;
    float translated_y = gr->GetY()[i] + y0;

    gr->SetPoint(i,translated_x,translated_y);

  }

}
//


TGraph* HGCalSysValDigisHarvester::getModuleBin(TFile* file, bool isSiPM,int plane,int u, int v){
    
    TGraph* gr = nullptr;
    
    std::ostringstream oss;
    oss << "/isSiPM_" << int(isSiPM)
            << "/plane_" << plane
            << "/u_" << u
            << "/v_" << v;
    
    std::string moduleDir = oss.str();  
    

    if (!file->cd(moduleDir.c_str())) {
        std::cerr << "Could not cd to directory!" << std::endl;
        return nullptr;
    }
    
    gr = dynamic_cast<TGraph*>(gDirectory->Get("module_bin"));
    
    if (!gr){
        std::cerr << "Error: Bin not found!" << std::endl;
        return nullptr;
    }
    
    
    file->cd("/");
    
    return gr;
    
}


std::vector<double> HGCalSysValDigisHarvester::getModuleCenter(TFile* file, bool isSiPM,int plane,int u, int v){
    
    std::vector<double> x0y0(2,0);
    std::ostringstream oss;
    oss << "/isSiPM_" << int(isSiPM)
            << "/plane_" << plane
            << "/u_" << u
            << "/v_" << v;
    
    std::string moduleDir = oss.str();  

    if (!file->cd(moduleDir.c_str())) {
        std::cerr << "Could not cd to directory!" << std::endl;
        return x0y0;
    }
    
    TTree* tree = dynamic_cast<TTree*>(gDirectory->Get("module_properties"));
    
    if (!tree){
        std::cerr << "Error: TTree not found!" << std::endl;
        return x0y0;    
    }
    
    double x0,y0;
    
    tree->SetBranchAddress("x0",&x0);
    tree->SetBranchAddress("y0",&y0);
    if (!(tree->GetEntries()>0)){
      std::cerr << "TTree empty" << std::endl;
    }

    tree->GetEntry(0);
    x0y0[0] = x0; x0y0[1] = y0;
    
    // Restore original directory (usually root of the file)
    gDirectory->cd("/");
    delete tree;
    return x0y0;
} 


void HGCalSysValDigisHarvester::dqmEndJob(DQMStore::IBooker &ibooker, DQMStore::IGetter &igetter) {}

DEFINE_FWK_MODULE(HGCalSysValDigisHarvester);
