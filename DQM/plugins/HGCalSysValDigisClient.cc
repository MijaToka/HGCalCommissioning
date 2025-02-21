#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DQMServices/Core/interface/DQMEDAnalyzer.h"
#include "DQMServices/Core/interface/MonitorElement.h"


#include "DataFormats/HGCalDigi/interface/HGCalDigiHost.h"
#include "DataFormats/HGCalDigi/interface/HGCalECONDPacketInfoSoA.h"
#include "DataFormats/HGCalDigi/interface/HGCalECONDPacketInfoHost.h"
#include "DataFormats/HGCalDigi/interface/HGCalRawDataDefinitions.h"
#include "HGCalCommissioning/HGCalDigiTrigger/interface/HGCalDigiTriggerHost.h"

#include "CondFormats/DataRecord/interface/HGCalDenseIndexInfoRcd.h"
#include "CondFormats/DataRecord/interface/HGCalElectronicsMappingRcd.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingModuleIndexer.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingParameterHost.h"

#include "HGCalCommissioning/DQM/interface/HGCalSysValDQMCommon.h"
#include "HGCalCommissioning/SystemTestEventFilters/interface/HGCalTestSystemMetaData.h"
#include "DataFormats/FEDRawData/interface/FEDRawDataCollection.h"

#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalModuleIndexerTrigger.h"

#include <TString.h>

#include <string>
#include <fstream>
#include <iostream>
#include <map>

using namespace edm;
using namespace hgcal::dqm;

/**
   @short simple DQM client to monitor basic quantities at DIGI level from modules
   @author Yu-Wei Kao, P. Silva
*/
class HGCalSysValDigisClient : public DQMEDAnalyzer {
public:

  /** 
   @short helper structure with the basic information of a monitored element. 
   dqmIndex is a internal index for the number of the histogram
  */
  struct MonitoredElement_t {
    std::string typecode;
    bool zside, isSiPM;
    uint32_t layer, i1, i2, nErx, dqmIndex;
  };
  typedef std::pair<uint32_t,uint32_t> MonitoredElementKey_t;

  /**
   * @short CTOR
   */
  explicit HGCalSysValDigisClient(const edm::ParameterSet&);

  /**
   * @short DTOR
   */
  ~HGCalSysValDigisClient() override;

  /**
     @short method fills 'descriptions' with the allowed parameters for the module and their default values  
  */
  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

private:
  /**
    @short takes care of booking the monitoring elements at the start of the run
    the histograms are instantiated per module according to the module mapping
    received from the event setup
   */
  void bookHistograms(DQMStore::IBooker&, edm::Run const&, edm::EventSetup const&) override;

  /**
    @short histogram filler per event
   */
  void analyze(const edm::Event&, const edm::EventSetup&) override;
  void analyzeECONDFlags(const edm::Event& iEvent, const edm::EventSetup& iSetup);
  void analyzeModules(const edm::Event& iEvent, const edm::EventSetup& iSetup, int trigTime);
  void analyzeTriggerModules(const edm::Event& iEvent, const edm::EventSetup& iSetup, int trigTime);

  /** 
    @short for each module finds the channel with largest delta ADC to be used for special monitoring histograms
  */
  void findModuleSeeds(uint32_t minProcessed=500);

  // ------------ member data ------------
  const edm::EDGetTokenT<FEDRawDataCollection> fedRawToken_;
  const edm::EDGetTokenT<hgcaldigi::HGCalDigiHost> digisTkn_;
  const edm::EDGetTokenT<hgcaldigi::HGCalDigiTriggerHost> digisTriggerTkn_;
  const edm::EDGetTokenT<hgcaldigi::HGCalECONDPacketInfoHost> econdInfoTkn_;
  const edm::EDGetTokenT<HGCalTestSystemMetaData> metaDataTkn_;
  edm::ESGetToken<HGCalMappingModuleIndexer, HGCalElectronicsMappingRcd> moduleIdxTkn_;
  edm::ESGetToken<hgcal::HGCalMappingModuleParamHost, HGCalElectronicsMappingRcd> moduleInfoTkn_;
  edm::ESGetToken<hgcal::HGCalDenseIndexInfoHost, HGCalDenseIndexInfoRcd> denseIndexInfoTkn_;
  const std::vector<unsigned int> fedList_;
  const unsigned int  minEvents_;
  const unsigned int prescaleFactor_;
  unsigned int nProcessed_;
  std::map<MonitoredElementKey_t,MonitoredElement_t> followedModules_;
  std::map<std::string, std::map<MonitoredElementKey_t, MonitorElement*> > moduleHistos_;
  std::map<MonitoredElementKey_t, uint32_t> moduleSeeds_;

  MonitorElement *trigTimeH_,*trigTypeH_;
  MonitorElement *econdQualityH_, *cbQualityH_, *econdPayload_;

  HGCalModuleIndexerTrigger moduleIndexerTrigger_;
  std::map<std::string, std::map<uint32_t, MonitorElement*> > moduleTriggerHistos_;

  std::vector<std::string> BXlist = {"BXm3", "BXm2", "BXm1", "BX0", "BXp1", "BXp2", "BXp3"};
};


//
HGCalSysValDigisClient::HGCalSysValDigisClient(const edm::ParameterSet& iConfig)
    : fedRawToken_(consumes<FEDRawDataCollection>(iConfig.getParameter<edm::InputTag>("Raw"))),
      digisTkn_(consumes<hgcaldigi::HGCalDigiHost>(iConfig.getParameter<edm::InputTag>("Digis"))),
      digisTriggerTkn_(consumes<hgcaldigi::HGCalDigiTriggerHost>(iConfig.getParameter<edm::InputTag>("DigisTrigger"))),
      econdInfoTkn_(consumes<hgcaldigi::HGCalECONDPacketInfoHost>(iConfig.getParameter<edm::InputTag>("ECONDPacketInfo"))), //FlaggedECONDInfo
      metaDataTkn_(consumes<HGCalTestSystemMetaData>(iConfig.getParameter<edm::InputTag>("MetaData"))),
      moduleIdxTkn_(esConsumes<edm::Transition::BeginRun>()),
      moduleInfoTkn_(esConsumes<edm::Transition::BeginRun>()),
      denseIndexInfoTkn_(esConsumes()),
      fedList_(iConfig.getParameter<unsigned int>("FEDList")),
      minEvents_(iConfig.getParameter<unsigned int>("MinimumEvents")),
      prescaleFactor_(std::max(1u, iConfig.getParameter<unsigned int>("PrescaleFactor"))),
      nProcessed_(0) { }

//
HGCalSysValDigisClient::~HGCalSysValDigisClient() { LogDebug("HGCalSysValDigisClient") << "End of the job" << std::endl; }

//
void HGCalSysValDigisClient::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("Raw", edm::InputTag("rawDataCollector",""));
  desc.add<edm::InputTag>("Digis", edm::InputTag("hgcalDigis", ""));
  desc.add<edm::InputTag>("DigisTrigger", edm::InputTag("hgcalDigis", "HGCalDigiTrigger"));
  desc.add<edm::InputTag>("ECONDPacketInfo", edm::InputTag("hgcalDigis", "")); //UnpackerFlags
  desc.add<edm::InputTag>("MetaData", edm::InputTag("rawMetaDataCollector", ""));
  desc.add<unsigned int>("FEDList", {0});
  desc.add<unsigned int>("MinimumEvents", 10000);
  desc.add<unsigned int>("PrescaleFactor", 1);
  descriptions.addWithDefaultLabel(desc);
}

//
void HGCalSysValDigisClient::analyze(const edm::Event& iEvent, const edm::EventSetup& iSetup) {

  ++nProcessed_;

  //trigger time
  const auto& metadata = iEvent.get(metaDataTkn_);
  int trigTime = metadata.trigTime_;
  trigTimeH_->Fill(trigTime);
  int trigType=metadata.trigType_;
  int trigSubType=metadata.trigSubType_;
  for(size_t i=0; i<6; i++) {
    bool hasType((trigType>>i) & 0x1);
    if(!hasType) continue;
    for(size_t j=0; j<2; j++) {
      bool hasSubType((trigSubType>>j) & 0x1);
      if(!hasSubType) continue;
      trigTypeH_->Fill(i,j);
    }
  }

  analyzeECONDFlags(iEvent,iSetup);

  //check if this an event which should be tracked
  bool toProcess = (nProcessed_ < minEvents_) || (nProcessed_ % prescaleFactor_ == 0);
  if (!toProcess)
    return;
  
  analyzeModules(iEvent,iSetup,trigTime);
  analyzeTriggerModules(iEvent,iSetup,trigTime);
  findModuleSeeds();
}  

//
void HGCalSysValDigisClient::analyzeModules(const edm::Event& iEvent, const edm::EventSetup& iSetup, int trigTime) {

  //read digis and dense index info
  const auto& digis = iEvent.getHandle(digisTkn_);
  const auto& digis_view = digis->const_view();
  int32_t ndigis = digis_view.metadata().size();
  const auto& denseIndexInfo = iSetup.getData(denseIndexInfoTkn_);
  const auto& denseIndexInfo_view = denseIndexInfo.const_view();
  int32_t ndii = denseIndexInfo_view.metadata().size();
  assert( ndigis == ndii );

  //loop to fill histograms
  std::map<MonitoredElementKey_t, uint32_t> seedDigiIdx;
  for (int32_t i = 0; i < ndigis; ++i) {

    //skip digis not tracked
    auto indexinfo = denseIndexInfo_view[i];
    MonitoredElementKey_t key(indexinfo.fedId(), indexinfo.fedReadoutSeq());
    if(followedModules_.find(key) == followedModules_.end()) continue;

    //channel index
    uint32_t chIdx = indexinfo.chNumber();

    //check if this is a module seed for later filling of dedicated histograms
    if(moduleSeeds_.find(key)!=moduleSeeds_.end() && moduleSeeds_[key]==chIdx) seedDigiIdx[key]=i;

    //decode digis
    auto digi = digis_view[i];
    uint8_t tctp = digi.tctp();
    double adc = digi.adc();
    double tot = digi.tot();
    double toa = digi.toa();
    double adcm = digi.adcm1();
    double cmsum = digi.cm();
    uint16_t flags = digi.flags();
    double deltaadc = adc-adcm;

    //NOTE: Probably should check that flags==0
    //and have an histogram for flags!=0 ?
    if(flags==hgcal::DIGI_FLAG::NotAvailable) continue; // quick quality check for TB2024
    if(adc<0 && tot<0) continue;

    //start channel sums (this will be further corrected down depending on the availability
    std::vector<double> tosum(SumIndices_t::LASTINDEX,0);
    tosum[SumIndices_t::NCM] = 1;
    tosum[SumIndices_t::SUMCM] = cmsum;

    moduleHistos_["occupancy"][key]->Fill(chIdx);

    //ADC mode
    if ( tctp==0 ) {
      moduleHistos_["avgadc"][key]->Fill(chIdx,adc);
      moduleHistos_["adc"][key]->Fill(adc);
      moduleHistos_["avgadcm1"][key]->Fill(chIdx,adcm);
      moduleHistos_["adcm1"][key]->Fill(adcm);
      moduleHistos_["avgdeltaadc"][key]->Fill(chIdx,deltaadc);
      moduleHistos_["deltaadc"][key]->Fill(deltaadc);
      tosum[SumIndices_t::NADC]=1;   tosum[SumIndices_t::SUMADC]=adc;    tosum[SumIndices_t::SUMADC2]=adc*adc;
      tosum[SumIndices_t::NADCM1]=1; tosum[SumIndices_t::SUMADCM1]=adcm; tosum[SumIndices_t::DELTAADC]=deltaadc;
    } else{
      tosum[SumIndices_t::NADC]=0;   tosum[SumIndices_t::SUMADC]=0;   tosum[SumIndices_t::SUMADC2]=0;
      tosum[SumIndices_t::NADCM1]=0; tosum[SumIndices_t::SUMADCM1]=0; tosum[SumIndices_t::DELTAADC]=0;
    }

    //TOT mode
    if ( tctp==3 ) {
      moduleHistos_["avgtot"][key]->Fill(chIdx,tot);
      moduleHistos_["tot"][key]->Fill(tot);
      tosum[SumIndices_t::NTOT]=1; tosum[SumIndices_t::SUMTOT]=tot;
    } else {
      tosum[SumIndices_t::NTOT]=0; tosum[SumIndices_t::SUMTOT]=0;
    }

    //Valid TOA
    if ( toa>0 ) {
      moduleHistos_["avgtoa"][key]->Fill(chIdx,toa);
      moduleHistos_["toa"][key]->Fill(toa);
      tosum[SumIndices_t::NTOA]=1; tosum[SumIndices_t::SUMTOA]=toa;
    } else {
      tosum[SumIndices_t::NTOA]=0; tosum[SumIndices_t::SUMTOA]=0;
    }

    //update sums in the corresponding bins
    for(size_t ibin=0; ibin<SumIndices_t::LASTINDEX; ibin++) {
      auto newVal = tosum[ibin] + moduleHistos_["sums"][key]->getBinContent(chIdx+1, ibin+1);
      moduleHistos_["sums"][key]->setBinContent(chIdx+1, ibin+1, newVal);
    }

  } // end digis loop

  //histograms for best S/N candidate cells
  if(seedDigiIdx.size()==0) return;
  for(auto it : seedDigiIdx) {
    auto key = it.first;
    auto digiIdx = it.second;
    auto digi = digis_view[digiIdx];
    moduleHistos_["seedadc"][key]->Fill(digi.adc());
    moduleHistos_["seedtoa"][key]->Fill(digi.toa());    
    moduleHistos_["seedadcvstrigtime"][key]->Fill(trigTime,digi.adc());
    moduleHistos_["seedtoavstrigtime"][key]->Fill(trigTime,digi.toa());    
  }

}

void HGCalSysValDigisClient::analyzeTriggerModules(const edm::Event& iEvent, const edm::EventSetup& iSetup, int trigTime) {
  const auto& digisTrigger = iEvent.getHandle(digisTriggerTkn_);
  const auto& digisTrigger_view = digisTrigger->const_view();
  int32_t ndigisTrigger = digisTrigger_view.metadata().size();

  // TODO: replace with proper mapping
  moduleIndexerTrigger_.setLayerOffset(1000);
  moduleIndexerTrigger_.setModOffset(100);
  moduleIndexerTrigger_.setMaxLayer(10);
  moduleIndexerTrigger_.setMaxMod(10);
  moduleIndexerTrigger_.setMaxCh(100);

  //loop to fill histograms
  for (int32_t i = 0; i < ndigisTrigger; ++i) {
    
    auto digiTrigger = digisTrigger_view[i];

    if (digiTrigger.flags() == hgcal::DIGI_FLAG::NotAvailable) continue;
      
      //decode digis
      int algo = static_cast<int>(digiTrigger.algo());
      int valid = static_cast<int>(digiTrigger.valid());
      int moduleIdx = static_cast<int>(digiTrigger.moduleIdx());
      int layer = static_cast<int>(digiTrigger.layer());
      
      uint32_t modidx = moduleIndexerTrigger_.getIndexForModuleData(layer, moduleIdx, 0);
      moduleTriggerHistos_["algo"][modidx]->Fill(algo);
      moduleTriggerHistos_["valid"][modidx]->Fill(valid);
      
      std::vector<int> BXlocations = {
        static_cast<int>(digiTrigger.BXm3_location()),
        static_cast<int>(digiTrigger.BXm2_location()),
        static_cast<int>(digiTrigger.BXm1_location()),
        static_cast<int>(digiTrigger.BX0_location()),
        static_cast<int>(digiTrigger.BXp1_location()),
        static_cast<int>(digiTrigger.BXp2_location()),
        static_cast<int>(digiTrigger.BXp3_location()),
      };
      std::vector<double> BXenergies = {
        static_cast<double>(digiTrigger.BXm3_energy()),
        static_cast<double>(digiTrigger.BXm2_energy()),
        static_cast<double>(digiTrigger.BXm1_energy()),
        static_cast<double>(digiTrigger.BX0_energy()),
        static_cast<double>(digiTrigger.BXp1_energy()),
        static_cast<double>(digiTrigger.BXp2_energy()),
        static_cast<double>(digiTrigger.BXp3_energy()),
      };
      int nominal_BX_location = BXlocations[3];
      uint32_t chidx = moduleIndexerTrigger_.getIndexForModuleData(layer, moduleIdx, nominal_BX_location);

      for(long unsigned int i = 0; i<BXlist.size(); i++) {
        moduleTriggerHistos_[BXlist[i]+"_location"][chidx]->Fill(BXlocations[i]);
        moduleTriggerHistos_[BXlist[i]+"_energy"][chidx]->Fill(BXenergies[i]);
      }
  }
}

//
void HGCalSysValDigisClient::findModuleSeeds(uint32_t minProcessed) {

  if(nProcessed_<minProcessed) return;
  if(moduleSeeds_.size()>0) return;

  //loop over sums histos
  for(auto it : moduleHistos_["sums"]) {
    auto key = it.first;
    auto h = it.second;

    //find the channel which is more promising in S/N
    double maxDeltaADC(-1);
    int seedCandidate(0);
    for(int xbin=0; xbin<h->getNbinsX(); xbin++) {
      double deltaADC = h->getBinContent(xbin+1,SumIndices_t::DELTAADC+1);
      if(deltaADC<maxDeltaADC) continue;
      maxDeltaADC = deltaADC;
      seedCandidate = xbin;
    }

    //set as seed
    moduleSeeds_[key]=seedCandidate;
  }

}

//
void HGCalSysValDigisClient::analyzeECONDFlags(const edm::Event& iEvent, const edm::EventSetup& iSetup) {

  //read module info flagged ECON-D list
  const auto& econdInfo = iEvent.getHandle(econdInfoTkn_); // ECON-D packet flags
  if (!econdInfo.isValid()) return;

  const auto& raw_data = iEvent.getHandle(fedRawToken_);

  //find bin for each econ and fill its histograms
  // Flags are described in DataFormats/HGCalDigi/interface/HGCalECONDPacketInfoSoA.h
  for(auto it : followedModules_) {

    const uint32_t imod = it.second.dqmIndex; // global/dense module index
    const auto econd = econdInfo->const_view()[imod];

    econdPayload_->Fill(imod,econd.payloadLength());
    if (!(econd.cbFlag() & 0b1000)){
	    cbQualityH_->Fill(imod,(econd.cbFlag() & 0b0111));
    }
    else{
	    cbQualityH_->Fill(imod,(econd.cbFlag() & 0b1000));
    }
    if (econd.cbFlag() & 0b111) econdQualityH_->Fill(imod, 0);
    auto htflags=hgcaldigi::htFlag(econd.econdFlag());
    auto eboflags=hgcaldigi::eboFlag(econd.econdFlag());
    if (htflags>0) econdQualityH_->Fill(imod, 0 + htflags);
    if (eboflags>0) econdQualityH_->Fill(imod, 3 + eboflags);
    if (hgcaldigi::matchFlag(econd.econdFlag())==0) econdQualityH_->Fill(imod, 7);
    if (hgcaldigi::truncatedFlag(econd.econdFlag())) econdQualityH_->Fill(imod, 8);
    if (hgcaldigi::expectedFlag(econd.econdFlag())==0) econdQualityH_->Fill(imod, 9);
    if (hgcaldigi::StatFlag(econd.econdFlag())==1) econdQualityH_->Fill(imod, 10);
    if (econd.exception()==3) econdQualityH_->Fill(imod, 11); // wrongHeaderMarker
    if (econd.exception()==4) econdQualityH_->Fill(imod, 12); // payloadOverflows
    if (econd.exception()==5) econdQualityH_->Fill(imod, 13); // payloadMismatches
  }

}

//
void HGCalSysValDigisClient::bookHistograms(DQMStore::IBooker& ibook, edm::Run const& run, edm::EventSetup const& iSetup) {

  //create module keys only for FEDs in the FED list
  const auto& moduleIndexer = iSetup.getData(moduleIdxTkn_);
  const auto& moduleInfo = iSetup.getData(moduleInfoTkn_);

  //loop over available modules in the system and select the ones to be tracked
  for(const auto &it : moduleIndexer.getTypecodeMap()) {
    uint32_t fedid = it.second.first;
    if(fedList_.size()>0 && std::find(fedList_.begin(), fedList_.end(), fedid) == fedList_.end()) continue;

    std::string typecode = it.first;
    std::replace(typecode.begin(), typecode.end(), '-', '_');
    uint32_t imod = it.second.second; // local module index for this FED (readout sequence)
    uint32_t denseModIdx = moduleIndexer.getIndexForModule(fedid, imod); // global/dense module index
    const auto modInfo = moduleInfo.view()[denseModIdx];

    MonitoredElement_t ele;    
    ele.dqmIndex = denseModIdx;
    ele.typecode = typecode;
    ele.nErx = moduleIndexer.getMaxERxSize(fedid, imod); 
    ele.zside = modInfo.zside();
    ele.isSiPM = modInfo.isSiPM();
    ele.layer = modInfo.plane();
    ele.i1 = modInfo.i1();
    ele.i2 = modInfo.i2();
    followedModules_[ MonitoredElementKey_t(fedid,imod) ] = ele;
  }
  size_t nmods(followedModules_.size());
  LogDebug("HGCalSysValDigisClient") << "Read module info with " << nmods << " entries";

  //book monitoring elements (histos, profiles, etc.)
  ibook.setCurrentFolder("HGCAL/Digis");
 
  //trigtime and trigtype
  trigTypeH_ = ibook.book2D("trigtype", ";Trigger Type; Trigger SubType; Counts", 6,0,6,2,0,2);
  std::vector<std::string> trigtypes = { "Phys", "Calib" , "Random" ,"SW", "Reserve4", "Reserve5"};
  std::vector<std::string> trigsubtypes = { "ECON-T","Ext."};
  for(size_t i=0; i<trigtypes.size(); i++)
    trigTypeH_->setBinLabel(i+1,trigtypes[i],1);
  for(size_t i=0; i<trigsubtypes.size(); i++)
    trigTypeH_->setBinLabel(i+1,trigsubtypes[i],2);
  trigTimeH_ = ibook.book1D("trigtime", ";trigger phase; Counts", 200, 0, 200);

  //ECON-D flags and payload
  //the last loop also instantiates the per module histograms (besides setting the bin labels of ECON-D names)
  econdPayload_ = ibook.book2D("econdPayload", ";ECON-D;Payload", nmods, 0, nmods, 200, 0, 500);

  std::vector<std::string> econdflags = {
    "CB",
    "H/T good",    "H/T fail",    "H/T amb",
    "E/B/O good",  "E/B/O fail",  "E/B/O amb",
    "Unmatched (M)",   "Trunc (T)", "Unexpected (E)", "Sub-packet error (S)",
    "Marker", "Payload (OF)", "Payload (mismatch)"};
  size_t necondflags = econdflags.size();
  econdQualityH_ = ibook.book2D("econdQualityH", ";ECON-D;Header quality;", nmods, 0, nmods, necondflags, 0, necondflags);
  for(size_t i=0; i<necondflags; i++) econdQualityH_->setBinLabel(i+1, econdflags[i].c_str(), 2);

  std::vector<std::string> cbflags = {"Normal","Payload","CRC Error","EvID Mis.","FSM T/O","BCID/OrbitID","MB Overflow","Innactive","CRC trailer error"};
  size_t ncbflags = cbflags.size();
  cbQualityH_ = ibook.book2D("cbQualityH", ";ECON-D;DAQ quality flags", nmods, 0, nmods, ncbflags, 0, ncbflags);
  for(size_t i=0; i<ncbflags; i++) cbQualityH_->setBinLabel(i+1, cbflags[i].c_str(), 2);

  size_t xbin(0);
  for(auto it : followedModules_) {
    xbin = it.second.dqmIndex;
    xbin++;

    //label the econ-D histograms with typecodes
    std::string typecode = it.second.typecode;
    auto binlabel = typecode.c_str();
    econdQualityH_->setBinLabel(xbin, binlabel, 1);
    cbQualityH_->setBinLabel(xbin, binlabel, 1);
    econdPayload_->setBinLabel(xbin, binlabel, 1);

    //Per module histograms
    auto k = it.first;
    size_t nch = it.second.nErx*37;

    std::ostringstream ss;
    ss << "_module_" << it.second.dqmIndex;
    std::string tag(ss.str());

    moduleHistos_["occupancy"][k] = ibook.book1D("occupancy" + tag, typecode + ";Channel; #hits", nch, -0.5, nch-0.5);
    moduleHistos_["avgadc"][k] = ibook.bookProfile("avgadc" + tag, typecode + ";Channel; <ADC>", nch, -0.5, nch-0.5, 100, 0, 1024);
    moduleHistos_["adc"][k] = ibook.book1D("adc" + tag, typecode + ";ADC; Counts (all channels)", 100, 0, 1024);
    moduleHistos_["avgtot"][k] = ibook.bookProfile("avgtot" + tag, typecode + ";Channel; <TOT>", nch, -0.5, nch-0.5, 100, 0, 1024);
    moduleHistos_["tot"][k] = ibook.book1D("tot" + tag, typecode + ";TOT; Counts (all channels)", 100, 0, 4096);
    moduleHistos_["avgadcm1"][k] = ibook.bookProfile("avgadcm1" + tag, typecode + ";Channel; <ADC(-1)>", nch, -0.5, nch-0.5, 100, 0, 1024);
    moduleHistos_["adcm1"][k] = ibook.book1D("adcm1" + tag, typecode + ";ADC_{-1}; Counts (all channels)", 100, 0, 1024);
    moduleHistos_["avgtoa"][k] = ibook.bookProfile("avgtoa" + tag, typecode + ";Channel; <TOA>", nch, -0.5, nch-0.5, 100, 0, 1024);
    moduleHistos_["toa"][k] = ibook.book1D("toa" + tag, typecode + ";TOA; Counts (all channels)", 100, 0, 1024);
    moduleHistos_["avgdeltaadc"][k] = ibook.bookProfile("avgdeltaadc" + tag, typecode + ";Channel; <ADC-ADC_{-1}>", nch, -0.5, nch-0.5, 100, 0, 1024);
    moduleHistos_["deltaadc"][k] = ibook.book1D("deltaadc" + tag, typecode + ";ADC-ADC_{-1}; Counts (all channels)", 100, -200, 200);
    moduleHistos_["seedadc"][k] = ibook.book1D("seedadc" + tag, typecode + ";ADC of channel with max <ADC-ADC_{-1}>; Counts", 100, 0, 1024);
    moduleHistos_["seedadcvstrigtime"][k] = ibook.book2D(
        "seedadcvstrigtime" + tag, typecode + ";trigger phase; ADC of channel with max <ADC-ADC_{-1}>", 200, 0, 200, 100, 0, 1024);
    moduleHistos_["seedtoa"][k] = ibook.book1D("seedtoa" + tag, typecode + ";TOA of channel with max <ADC-ADC_{-1}>; Counts", 100, 0, 1024);
    moduleHistos_["seedtoavstrigtime"][k] = ibook.book2D(
        "seedtoavstrigtime" + tag, typecode + ";trigger phase; TOA of channel with max <ADC-ADC_{-1}>", 200, 0, 200, 100, 0, 1024);
    
    //sums will be used bt the harvester
    moduleHistos_["sums"][k] = ibook.book2D("sums" + tag, typecode + ";Channel;", nch, 0, nch, SumIndices_t::LASTINDEX,0,SumIndices_t::LASTINDEX);
    for(size_t i=0; i<SumIndices_t::LASTINDEX; i++) {
      std::string label = getLabelForSumIndex(SumIndices_t(i));
      moduleHistos_["sums"][k]->setBinLabel(i+1, label, 2);
    }

  }// end followedModules_ loop

  // Trigger histograms
  moduleIndexerTrigger_.setLayerOffset(1000);
  moduleIndexerTrigger_.setModOffset(100);
  moduleIndexerTrigger_.setMaxLayer(10);
  moduleIndexerTrigger_.setMaxMod(10);
  moduleIndexerTrigger_.setMaxCh(100);

  //int maxIdx = static_cast<int>(moduleIndexerTrigger_.getMaxIndex());
  uint32_t layers = 2;
  uint32_t modids = 3;
  uint32_t chs = 48;
  
  for (uint32_t layer = 0; layer < layers; layer++) {
    for (uint32_t modid = 0; modid < modids; modid++) {
      uint32_t modidx = moduleIndexerTrigger_.getIndexForModuleData(layer, modid, 0);
      std::ostringstream ss;
      ss << "_layer_" << layer << "_module_" << modid;
      std::string tag(ss.str());
      moduleTriggerHistos_["algo"][modidx] = ibook.book1D("algo" + tag, "Algo; Algo; Counts", 10, 0, 10);
      moduleTriggerHistos_["valid"][modidx] = ibook.book1D("valid" + tag, "valid; valid; Counts", 10, 0, 10);
      for (uint32_t ch = 0; ch < chs; ch++) {
        uint32_t chidx = moduleIndexerTrigger_.getIndexForModuleData(layer, modid, ch);
        std::ostringstream ssCh;
        ssCh << "_layer_" << layer << "_module_" << modid << "_channel_" << ch;
        std::string tagCh(ssCh.str());
        for (unsigned long int i = 0; i < BXlist.size(); i++) {
          std::string BX = BXlist[i];
          moduleTriggerHistos_[BX + "_location"][chidx] = ibook.book1D(BX + "_location" + tagCh, BX + "_location; " + BX + "_location; Counts", 50, 0, 50);
          moduleTriggerHistos_[BX + "_energy"][chidx] = ibook.book1D(BX + "_energy" + tagCh, BX + "_energy; " + BX + "_energy; Counts", 100, 0, 100);
        }
      }
    }
  }

}

// define this as a plug-in
DEFINE_FWK_MODULE(HGCalSysValDigisClient);
