// system include files
#include <memory>
#include <iostream>
#include <sstream>
#include <string>

// user include files
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/Utilities/interface/Span.h"

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"

#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/StreamID.h"

#include "CommonTools/Utils/interface/StringCutObjectSelector.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"

//Meta data (trigger, ...)
#include "HGCalCommissioning/SystemTestEventFilters/interface/HGCalTestSystemMetaData.h"
//DetId
#include "DataFormats/ForwardDetId/interface/HGCalDetId.h"
//Digi information
#include "DataFormats/HGCalDigi/interface/HGCalDigiHost.h"
#include "DataFormats/HGCalDigi/interface/HGCalRawDataDefinitions.h"
//RecHit information
#include "DataFormats/HGCalRecHit/interface/HGCalRecHitHost.h"
//mapping information
#include "CondFormats/DataRecord/interface/HGCalElectronicsMappingRcd.h"
#include "CondFormats/DataRecord/interface/HGCalDenseIndexInfoRcd.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingParameterHost.h"
#include "DataFormats/HGCalDigi/interface/HGCalECONDPacketInfoSoA.h"
#include "DataFormats/HGCalDigi/interface/HGCalECONDPacketInfoHost.h"
#include "FWCore/Utilities/interface/Exception.h"

#include <iostream>
class HGCalNanoTableProducer : public edm::stream::EDProducer<> {
public:
  explicit HGCalNanoTableProducer(const edm::ParameterSet& iConfig)
      : metadataToken_(consumes<HGCalTestSystemMetaData>(iConfig.getParameter<edm::InputTag>("metadata"))),
        digisToken_(consumes<hgcaldigi::HGCalDigiHost>(iConfig.getParameter<edm::InputTag>("digis"))),
        rechitsToken_(consumes<hgcalrechit::HGCalRecHitHost>(iConfig.getParameter<edm::InputTag>("rechits"))),
        econdInfoTkn_(consumes<hgcaldigi::HGCalECONDPacketInfoHost>(iConfig.getParameter<edm::InputTag>("econds"))),
        denseIndexInfoTkn_(esConsumes()),
        cellTkn_(esConsumes()),
        moduleTkn_(esConsumes()),
        skipMeta_(iConfig.getParameter<bool>("skipMeta")),
        skipDigi_(iConfig.getParameter<bool>("skipDigi")),
        skipECON_(iConfig.getParameter<bool>("skipECON")),
        skipRecHits_(iConfig.getParameter<bool>("skipRecHits")) {
    if( !skipMeta_) produces<nanoaod::FlatTable>("HGCMetaData");        
    if (!skipDigi_) produces<nanoaod::FlatTable>("HGCDigi");
    if (!skipECON_) produces<nanoaod::FlatTable>("HGCECON");
    if (!skipRecHits_) produces<nanoaod::FlatTable>("HGCHit");
  }

  ~HGCalNanoTableProducer() override {}

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("metadata", edm::InputTag("rawMetaDataCollector", ""))->setComment("Source of DIGIs SoA");
    desc.add<edm::InputTag>("digis", edm::InputTag("hgcalDigis", ""))->setComment("Source of DIGIs SoA");
    desc.add<edm::InputTag>("rechits", edm::InputTag("hgcalRecHits", ""))->setComment("Source of RecHits SoA");
    desc.add<edm::InputTag>("econds", edm::InputTag("hgcalDigis", ""))->setComment("Source of ECOND info SoA");
    desc.add<bool>("skipMeta", false)->setComment("Does not output Metadata table if enabled");
    desc.add<bool>("skipDigi", false)->setComment("Does not output DIGIs table if enabled");
    desc.add<bool>("skipRecHits", false)->setComment("Does not output RecHits table if enabled");
    desc.add<bool>("skipECON", false)->setComment("Does not output ECON table if enabled");
    descriptions.addWithDefaultLabel(desc);
  }

private:

  //digi table columns
  std::vector<uint16_t> tctp, adc, adcm1, tot, toa, cm, flags, channel, fedId, fedReadoutSeq;
  std::vector<int> chI1, chI2, modI1, modI2, chType;
  std::vector<bool> isSiPM;

  //rec hit table columns
  std::vector<float> energy,time,x,y;
  std::vector<int> layer;
  std::vector<uint16_t> rechitflags;
  std::vector<bool> zSide;
  
  void beginStream(edm::StreamID) override{};

  void produce(edm::Event& iEvent, const edm::EventSetup& iSetup) override {
    using namespace edm;

    //retrieve mapping parameters
    auto const& cellInfo = iSetup.getData(cellTkn_);
    auto const& cellInfo_view = cellInfo.const_view();
    auto const& moduleInfo = iSetup.getData(moduleTkn_);
    auto const& moduleInfo_view = moduleInfo.const_view();
    auto const& denseIndexInfo = iSetup.getData(denseIndexInfoTkn_);
    auto const& denseIndexInfo_view = denseIndexInfo.const_view();
    int32_t ndenseIndices = denseIndexInfo_view.metadata().size();

    //fill data for meta data if available
    const auto& metaData = iEvent.getHandle(metadataToken_);
    if(!skipMeta_ && metaData.isValid()) {
      auto outmetadata = std::make_unique<nanoaod::FlatTable>(1, "HGCMetaData", true); // singleton table
      outmetadata->setDoc("HGCal meta data");
      outmetadata->addColumnValue<uint32_t>("trigTime",    metaData->trigTime_,    "trigger time");
      outmetadata->addColumnValue<uint32_t>("trigWidth",   metaData->trigWidth_,   "trigger width");
      outmetadata->addColumnValue<uint32_t>("trigType",    metaData->trigType_,    "trigger type");
      outmetadata->addColumnValue<uint32_t>("trigSubType", metaData->trigSubType_, "trigger subtype");
      iEvent.put(std::move(outmetadata), "HGCMetaData");
    }
    
    //retrieve digis and rechits : check if they are valid and consistent with dense indices
    const auto& digis = iEvent.getHandle(digisToken_);
    int32_t ndigis = 0;
    if(!skipDigi_ && digis.isValid()) {
      ndigis = digis->const_view().metadata().size();
      assert(ndigis == ndenseIndices);
    }
    
    //retrieve rechits and ensure size matches that of dense indices
    const auto& rechits = iEvent.getHandle(rechitsToken_);
    int32_t nrechits = 0;
    if(!skipRecHits_ && rechits.isValid()) {
      nrechits = rechits->const_view().metadata().size();
      assert(nrechits == ndenseIndices);
    }
    
    size_t ngood = 0;
    
    //digi flattable (resize first event)
    if(tctp.size()==0 && !skipDigi_) {
      tctp.resize(ndenseIndices);
      chType.resize(ndenseIndices);
      adc.resize(ndenseIndices);
      adcm1.resize(ndenseIndices);
      tot.resize(ndenseIndices);
      toa.resize(ndenseIndices);
      cm.resize(ndenseIndices);
      flags.resize(ndenseIndices);
      channel.resize(ndenseIndices);
      fedId.resize(ndenseIndices);
      fedReadoutSeq.resize(ndenseIndices);
      chI1.resize(ndenseIndices);
      chI2.resize(ndenseIndices);
      modI1.resize(ndenseIndices);
      modI2.resize(ndenseIndices);    
      isSiPM.resize(ndenseIndices);
    }
    
    //rechit flattable (resize first event)
    if(energy.size()==0 && !skipRecHits_) {
      energy.resize(ndenseIndices);
      time.resize(ndenseIndices);
      x.resize(ndenseIndices);
      y.resize(ndenseIndices);
      layer.resize(ndenseIndices);
      rechitflags.resize(ndenseIndices);
      zSide.resize(ndenseIndices);
    }
    
    for (int32_t i = 0; i < ndenseIndices; i++) {
      
      //fill digis
      if(!skipDigi_) {
        auto const& digis_view = digis->const_view();
        if (digis_view.flags()[i] == hgcal::DIGI_FLAG::NotAvailable) continue;
	tctp[ngood] = digis_view.tctp()[i];
        adc[ngood] = digis_view.adc()[i];
        adcm1[ngood] = digis_view.adcm1()[i];
        tot[ngood] = digis_view.tot()[i];
        toa[ngood] = digis_view.toa()[i];
        cm[ngood] = digis_view.cm()[i];
        flags[ngood] = digis_view.flags()[i];
        channel[ngood] = denseIndexInfo_view.chNumber()[i];
        fedId[ngood] = denseIndexInfo_view.fedId()[i];
        fedReadoutSeq[ngood] = denseIndexInfo_view.fedReadoutSeq()[i];
        uint32_t cellInfoIdx(denseIndexInfo_view.cellInfoIdx()[i]);
        chType[ngood] = cellInfo_view.t()[cellInfoIdx];
        chI1[ngood] = cellInfo_view.i1()[cellInfoIdx];
        chI2[ngood] = cellInfo_view.i2()[cellInfoIdx];
        uint32_t modInfoIdx(denseIndexInfo_view.modInfoIdx()[i]);
	isSiPM[ngood] = moduleInfo_view.isSiPM()[modInfoIdx];
        modI1[ngood] = moduleInfo_view.i1()[modInfoIdx];
        modI2[ngood] = moduleInfo_view.i2()[modInfoIdx];
      }
      
      //fill rec hits
      if(!skipRecHits_) {
        auto const& rechits_view = rechits->const_view();
        energy[ngood] = rechits_view.energy()[i];
        time[ngood] = rechits_view.time()[i];
	rechitflags[ngood] = rechits_view.flags()[i];
        x[ngood] = denseIndexInfo_view.z()[i];
        y[ngood] = denseIndexInfo_view.y()[i];
        HGCalDetId detId(denseIndexInfo_view.detid()[i]);
        layer[ngood] = detId.layer();
        zSide[ngood] = detId.zside();
      }

      ngood++;
    }

    //wrap up the procedure of instatiating a span to copy only ngood values to a FlatTable
    //note in c++20 can use std::span instead
    auto addcol = []<typename T>(std::unique_ptr<nanoaod::FlatTable> &table, size_t n, const std::string &name, std::vector<T> &valvec, const std::string &docString)
      {
	edm::Span valvec_span(valvec.begin(),valvec.begin()+n);
	table->template addColumn<T>(name,valvec_span,docString);
      };

    //finalize digis table
    if(!skipDigi_) {     
      auto outdigi = std::make_unique<nanoaod::FlatTable>(ngood, "HGCDigi", false);
      outdigi->setDoc("HGC DIGIS");
      addcol(outdigi,ngood,"tctp",    tctp,    "Tc/Tp flags (2b)");
      addcol(outdigi,ngood,"adc",     adc,     "adc measurement");
      addcol(outdigi,ngood,"adcm1",   adcm1,   "adc measurement in BX-1");
      addcol(outdigi,ngood,"tot",     tot,     "tot measurement");
      addcol(outdigi,ngood,"toa",     toa,     "toa measurement");
      addcol(outdigi,ngood,"cm",      cm,      "common mode sum for the channels in the same halfROC / e-RX");
      addcol(outdigi,ngood,"flags",   flags,   "unpacking quality flags");
      addcol(outdigi,ngood,"chType",  chType,  "channel type: {0:calibration, 1:normal, -1: unconnected}");
      addcol(outdigi,ngood,"channel", channel, "sequential channel counting := (chip*2+half)*37 + 1/2 channel");
      addcol(outdigi,ngood,"isSiPM",  isSiPM,  "is SiPM-on-tile (false for Si)");
      addcol(outdigi,ngood,"modI1",   modI1,   "Si wafer U or tileboard iring coordinate");
      addcol(outdigi,ngood,"modI2",   modI2,   "Si wafer V or tileboard iphi coordinate");
      addcol(outdigi,ngood,"chI1",    chI1,    "Si channel U or tile iring coordinate");
      addcol(outdigi,ngood,"chI2",    chI2,    "Si channel V or tile iphi coordinate");
      addcol(outdigi,ngood,"fedId",   fedId,   "FED index");
      addcol(outdigi,ngood,"fedReadoutSeq", fedReadoutSeq, "ECON-D index in FED readout sequence");
      iEvent.put(std::move(outdigi), "HGCDigi");
    }
    
    //finalize rec hits table
    if(!skipRecHits_) {
      auto outhit = std::make_unique<nanoaod::FlatTable>(ngood, "HGCHit", false);
      outhit->setDoc("HGC RecHits");
      addcol(outhit,ngood,"energy", energy,      "calibrated energy");
      addcol(outhit,ngood,"time",   time,        "time");
      addcol(outhit,ngood,"flags",  rechitflags, "rec hit quality flags");
      addcol(outhit,ngood,"layer",  layer,       "layer");
      addcol(outhit,ngood,"x",      x,           "x coordinate from geometry");
      addcol(outhit,ngood,"y",      y,           "y coordinate from geometry");
      addcol(outhit,ngood,"zSide",  zSide,       "z side");
      iEvent.put(std::move(outhit), "HGCHit");
    }

    //fill table with ECON-D info
    const auto& econdInfo = iEvent.getHandle(econdInfoTkn_); // ECON-D packet flags
    if (!skipECON_ && econdInfo.isValid()) {
      auto const& econdInfo_view = econdInfo->const_view();
      int32_t necons = econdInfo_view.metadata().size();
      std::vector<uint16_t> payloads(necons);
      std::vector< std::vector<uint32_t> > cmsums(12);
      for(size_t ierx=0; ierx<12; ierx++) cmsums[ierx].resize(necons,0);
      for(int imod=0; imod<necons; imod++) {
        const auto econd = econdInfo_view[imod];
        payloads[imod] = econd.payloadLength();
        for(size_t ierx=0; ierx<12; ierx++)
          cmsums[ierx][imod] = econd.cm().coeff(ierx,0) + econd.cm().coeff(ierx,1);
      }
      auto outecon = std::make_unique<nanoaod::FlatTable>(necons, "HGCECON", false);
      outecon->setDoc("HGC ECON-D info");
      addcol(outecon,necons,"payload", payloads, "Decoded ECON-D payload");
      for(size_t ierx=0; ierx<12; ierx++) {
        std::ostringstream name;
        name << "cmsum" << ierx;
        std::ostringstream title;
        title << "Sum of common mode channels in e-Rx " + ierx;
        addcol(outecon,necons,name.str(), cmsums[ierx], title.str());
      }
      iEvent.put(std::move(outecon), "HGCECON");
    }
  }

  void endStream() override {};

  void beginRun(edm::Run const& iRun, edm::EventSetup const& iSetup) override {}

  // ----------member data ---------------------------
  const edm::EDGetTokenT<HGCalTestSystemMetaData> metadataToken_;
  const edm::EDGetTokenT<hgcaldigi::HGCalDigiHost> digisToken_;
  const edm::EDGetTokenT<hgcalrechit::HGCalRecHitHost> rechitsToken_;
  const edm::EDGetTokenT<hgcaldigi::HGCalECONDPacketInfoHost> econdInfoTkn_;
  edm::ESGetToken<hgcal::HGCalDenseIndexInfoHost, HGCalDenseIndexInfoRcd> denseIndexInfoTkn_;
  edm::ESGetToken<hgcal::HGCalMappingCellParamHost, HGCalElectronicsMappingRcd> cellTkn_;
  edm::ESGetToken<hgcal::HGCalMappingModuleParamHost, HGCalElectronicsMappingRcd> moduleTkn_;

  bool skipMeta_, skipDigi_, skipECON_, skipRecHits_;
};

//define this as a plug-in
DEFINE_FWK_MODULE(HGCalNanoTableProducer);
