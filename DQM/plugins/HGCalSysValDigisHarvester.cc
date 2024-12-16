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
  
  //location of the hex map templates
  std::string templateDir_;

  //module indexer / info
  edm::ESGetToken<HGCalMappingModuleIndexer, HGCalElectronicsMappingRcd> moduleIdxTkn_;
  edm::ESGetToken<hgcal::HGCalMappingModuleParamHost, HGCalElectronicsMappingRcd> moduleInfoTkn_;
  
  //monitoring elements
  MonitorElement *occupancyLayer_, *occupancyModule_, *meTimestamp_;
  std::map<unsigned int, MonitorElement *> hexLayerPlots_;
  std::map<std::string, std::map<std::string, MonitorElement *> > hexPlots_;  

  HGCalModuleIndexerTrigger moduleIndexerTrigger_;
  std::vector<std::string> BXlist = {"BXm3", "BXm2", "BXm1", "BX0", "BXp1", "BXp2", "BXp3"};
  std::map<int, char> irotstates_trigger = {{0,0},{1,1},{2,2}};

};

//
HGCalSysValDigisHarvester::HGCalSysValDigisHarvester(const edm::ParameterSet &iConfig)
  : templateDir_(iConfig.getParameter<std::string>("TemplateFiles")),
    moduleIdxTkn_(esConsumes<edm::Transition::EndLuminosityBlock>()),
    moduleInfoTkn_(esConsumes<edm::Transition::EndLuminosityBlock>())
{

}

//
void HGCalSysValDigisHarvester::fillDescriptions(edm::ConfigurationDescriptions &descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<std::string>("TemplateFiles","HGCalCommissioning/DQM/data");
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
  }

  //define layer-level summary
  ibooker.setCurrentFolder("HGCAL/Layers");
  size_t nLayers = 26; // NOTE: place holder for CE-E layers. Only two layers in 2024 beam test
  size_t nModules = typecodes.size();
  occupancyLayer_ = ibooker.book1D("summary_occupancy_layer", ";Layer; #hits", nLayers, 0.5, nLayers+0.5);
  occupancyModule_ = ibooker.book1D("summary_occupancy_module", ";Module; #hits", nModules, 0.5, nModules+0.5);
  float total_nHits_layer = 0; // M0, M1, M2 in layer1; M3, M4, M5 in layer2
  float total_nHits_module = 0; // nHits in each of six moodules

  // Get current timestamp
  auto now = std::chrono::system_clock::now();
  std::time_t timestamp = std::chrono::system_clock::to_time_t(now);
  TDatime dt(timestamp);
  TString timeString = dt.AsSQLString();
  std::cout << "Timestamp as TString: " << timeString.Data() << std::endl;
  meTimestamp_ = ibooker.bookString("info_timestamp", timeString);

  nLayers = 2;
  for(size_t i=0; i<nLayers; i++) {
    std::ostringstream ss, st;
    ss << "_layer_" << i+1;
    st << "Layer_" << i+1;
    std::string tag(ss.str());
    std::string title(st.str());

    //define layer-level hex plots
    hexLayerPlots_[i] = ibooker.book2DPoly("hex_occupancy"+tag,  title + "; x[cm]; y[cm];Occupancy", -50, 50, -50, 50);
  }

  //book the hex summary plots
  ibooker.setCurrentFolder("HGCAL/Modules");
  for(size_t i=0; i<typecodes.size(); i++) {
    
    std::string t = typecodes[i];
    char irot = irotstates[i];

    std::ostringstream ss;
    ss << "_module_" << i;
    std::string tag(ss.str());

    //set layer-level summary plots
    auto binlabel = t.c_str();
    occupancyModule_->setBinLabel(i+1, binlabel, 1);

    //define the hex plots
    hexPlots_[t]["avgcm"] = ibooker.book2DPoly("hex_avgcm"+tag,  t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::CMAVG), -14, 14, -14, 14);
    hexPlots_[t]["avgadc"] = ibooker.book2DPoly("hex_avgadc"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::PEDESTAL), -14, 14, -14, 14);
    hexPlots_[t]["stdadc"] = ibooker.book2DPoly("hex_stdadc"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::NOISE), -14, 14, -14, 14);
    hexPlots_[t]["deltaadc"] = ibooker.book2DPoly("hex_deltaadc"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::DELTAPEDESTAL), -14, 14, -14, 14);
    hexPlots_[t]["avgtoa"] = ibooker.book2DPoly("hex_avgtoa"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::TOAAVG), -14, 14, -14, 14);
    hexPlots_[t]["avgtot"] = ibooker.book2DPoly("hex_avgtot"+tag, t + "; x[cm]; y[cm];"+getLabelForSummaryIndex(SummaryIndices_t::TOTAVG), -14, 14, -14, 14);
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
      return std<0 ? -sqrt(fabs(std)) : sqrt(std);
    };

    //open file and loop over keys to hadd to THPoly (sequence of channel representations)
    std::string geourl = templateDir_ + "/geometry_" + t.substr(0,4) + "_wafer.root";
    edm::FileInPath fip(geourl);
    TFile *fgeo = new TFile(fip.fullPath().c_str(), "R");
    TKey *key;
    TIter nextkey(fgeo->GetDirectory(nullptr)->GetListOfKeys());
    uint32_t iobj(0);
    while ((key = (TKey *)nextkey())) {

      TObject *obj = key->ReadObj();
      if (!obj->InheritsFrom("TGraph")) continue;
      TGraph *gr = (TGraph *)obj;

      //skip CM channels
      bool isCM = (iobj % 39 == 37) || (iobj % 39 == 38);
      if(isCM) {
        iobj++;
        continue;
      }

      //apply rotation
      rotateShape(gr,irot);
      
      //compute summary for this standard channel
      unsigned eRx = int(iobj/39); //NOTE: CM channels were included in the objects
      unsigned chIdx = iobj - eRx*2;

      float nHits = num(SumIndices_t::NADC, chIdx, sum_me) + num(SumIndices_t::NTOT, chIdx, sum_me);
      total_nHits_layer += nHits;
      total_nHits_module += nHits;

      float avgcm = mean( SumIndices_t::SUMCM, SumIndices_t::NCM, chIdx, sum_me);
      hexPlots_[t]["avgcm"]->addBin(gr);
      hexPlots_[t]["avgcm"]->setBinContent(chIdx+1, avgcm);
      
      float avgadc = mean( SumIndices_t::SUMADC, SumIndices_t::NADC, chIdx, sum_me);
      hexPlots_[t]["avgadc"]->addBin(gr);
      hexPlots_[t]["avgadc"]->setBinContent(chIdx+1, avgadc);
      
      float stdadc = stddev( SumIndices_t::SUMADC2, SumIndices_t::SUMADC, SumIndices_t::NADC, chIdx, sum_me);
      hexPlots_[t]["stdadc"]->addBin(gr);
      hexPlots_[t]["stdadc"]->setBinContent(chIdx+1, stdadc);

      float deltaadc = avgadc - mean( SumIndices_t::SUMADCM1, SumIndices_t::NADCM1, chIdx, sum_me);
      hexPlots_[t]["deltaadc"]->addBin(gr);
      hexPlots_[t]["deltaadc"]->setBinContent(chIdx+1, deltaadc);

      float avgtoa = mean( SumIndices_t::SUMTOA, SumIndices_t::NTOA, chIdx, sum_me);
      hexPlots_[t]["avgtoa"]->addBin(gr);
      hexPlots_[t]["avgtoa"]->setBinContent(chIdx+1, avgtoa);

      float avgtot = mean( SumIndices_t::SUMTOT, SumIndices_t::NTOT, chIdx, sum_me);
      hexPlots_[t]["avgtot"]->addBin(gr);
      hexPlots_[t]["avgtot"]->setBinContent(chIdx+1, avgtot);

      hexPlots_[t]["occupancy"]->addBin(gr);
      float occval = occ_me->getBinContent(chIdx+1);
      hexPlots_[t]["occupancy"]->setBinContent(chIdx+1, occval);
      
      iobj++;
    }//end loop over template file keys

    //close template file
    fgeo->Close();

    //fill layer information
    occupancyModule_->setBinContent(i+1, total_nHits_module);
    total_nHits_module = 0.;
    if((i+1)%3==0) {
        occupancyLayer_->setBinContent((i+1)/3, total_nHits_layer);
        total_nHits_layer = 0.;
    }
  }//end loop over typecodes of this run

  //register layer-level geometry & fill bin contents
  unsigned int nModulesPerLayer=3;
  unsigned int layerModuleIdx=0;
  std::string geourl0 = templateDir_ + "/geometry_TB2024_wafers.root";
  edm::FileInPath fip0(geourl0);
  TFile *fgeo0 = new TFile(fip0.fullPath().c_str(), "R");
  TKey *key0;
  TIter nextkey0(fgeo0->GetDirectory(nullptr)->GetListOfKeys());
  while ((key0 = (TKey *)nextkey0())) {
    TObject *obj = key0->ReadObj();
    if (!obj->InheritsFrom("TGraph")) continue;
    TGraph *gr = (TGraph *)obj;
    for(size_t i=0; i<nLayers; i++) {
        int moduleIdx = nModulesPerLayer*i + layerModuleIdx;
        total_nHits_module = occupancyModule_->getBinContent(moduleIdx+1);
        hexLayerPlots_[i]->addBin(gr);
        hexLayerPlots_[i]->setBinContent(layerModuleIdx+1,total_nHits_module);
    }
    layerModuleIdx+=1;
  }
  fgeo0->Close();

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
  int nLayers = 2;
  int nModules = 3;
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
          char irot = irotstates_trigger[module];
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
  float angle(irot*M_PI/3.+5*M_PI/6.);
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

//
void HGCalSysValDigisHarvester::dqmEndJob(DQMStore::IBooker &ibooker, DQMStore::IGetter &igetter) {}

DEFINE_FWK_MODULE(HGCalSysValDigisHarvester);
