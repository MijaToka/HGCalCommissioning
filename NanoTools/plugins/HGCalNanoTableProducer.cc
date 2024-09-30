// system include files
#include <memory>

// user include files
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"

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

#include "FWCore/Utilities/interface/Exception.h"

#include <iostream>
class HGCalNanoTableProducer : public edm::stream::EDProducer<> {
public:
  explicit HGCalNanoTableProducer(const edm::ParameterSet& iConfig)
      : metadataToken_(consumes<HGCalTestSystemMetaData>(iConfig.getParameter<edm::InputTag>("metadata"))),
        digisToken_(consumes<hgcaldigi::HGCalDigiHost>(iConfig.getParameter<edm::InputTag>("digis"))),
        rechitsToken_(consumes<hgcalrechit::HGCalRecHitHost>(iConfig.getParameter<edm::InputTag>("rechits"))),
        denseIndexInfoTkn_(esConsumes()),
        cellTkn_(esConsumes()),
        moduleTkn_(esConsumes()),
        skipDigi_(iConfig.getParameter<bool>("skipDigi")),
        skipRecHits_(iConfig.getParameter<bool>("skipRecHits")) {
    produces<nanoaod::FlatTable>("HGCMetaData");        
    if (!skipDigi_)
      produces<nanoaod::FlatTable>("HGCDigi");
    if (!skipRecHits_)
      produces<nanoaod::FlatTable>("HGCHit");
  }

  ~HGCalNanoTableProducer() override {}

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("metadata", edm::InputTag("rawMetaDataCollector", ""))->setComment("Source of DIGIs SoA");
    desc.add<edm::InputTag>("digis", edm::InputTag("hgcalDigis", ""))->setComment("Source of DIGIs SoA");
    desc.add<edm::InputTag>("rechits", edm::InputTag("hgcalRecHits", ""))->setComment("Source of RecHits SoA");
    desc.add<bool>("skipDigi", false)->setComment("Does not output DIGIs table if enabled");
    desc.add<bool>("skipRecHits", false)->setComment("Does not output RecHits table if enabled");
    descriptions.addWithDefaultLabel(desc);
  }

private:
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

    //fill data for meta data
    const auto& metaData = iEvent.get(metadataToken_);
    auto outmetadata = std::make_unique<nanoaod::FlatTable>(1, "HGCMetaData", true); // singleton table
    outmetadata->setDoc("HGCal meta data");
    outmetadata->addColumnValue<uint32_t>("trigTime",    metaData.trigTime_,    "trigger time");
    outmetadata->addColumnValue<uint32_t>("trigWidth",   metaData.trigWidth_,   "trigger width");
    outmetadata->addColumnValue<uint32_t>("trigType",    metaData.trigType_,    "trigger type");
    outmetadata->addColumnValue<uint32_t>("trigSubType", metaData.trigSubType_, "trigger subtype");
    //outmetadata->addColumnValue<char>(    "injgain",     metaData.injgain_,     "injgain");
    //outmetadata->addColumnValue<uint32_t>("injcalib",    metaData.injcalib_,    "injcalib");
    iEvent.put(std::move(outmetadata), "HGCMetaData");

    //fill table for digis
    if (!skipDigi_) {

      //retrieve digis and ensure they are consistent with dense indices
      const auto& digis = iEvent.get(digisToken_);
      auto const& digis_view = digis.const_view();
      int32_t ndigis = digis_view.metadata().size();
      assert(ndigis == ndenseIndices);

      //auto outdigi = std::make_unique<nanoaod::FlatTable>(ndigis, "HGCDigi", false);
      //outdigi->setDoc("HGC DIGIS");
      //temporary hack
      //digi flattable
      std::vector<uint8_t> tctp(ndigis), chType(ndigis);
      std::vector<uint16_t> adc(ndigis), adcm1(ndigis), tot(ndigis), toa(ndigis), cm(ndigis), flags(ndigis),
          channel(ndigis), fedId(ndigis), fedReadoutSeq(ndigis);
      std::vector<int> chI1(ndigis), chI2(ndigis), modI1(ndigis), modI2(ndigis);
      std::vector<bool> isSiPM(ndigis);

      int ngooddigis = 0;
      for (int32_t i = 0; i < ndigis; i++) {
        if (digis_view.flags()[i] == hgcal::DIGI_FLAG::NotAvailable) continue;
        tctp[ngooddigis] = digis_view.tctp()[i];
        adc[ngooddigis] = digis_view.adc()[i];
        adcm1[ngooddigis] = digis_view.adcm1()[i];
        tot[ngooddigis] = digis_view.tot()[i];
        toa[ngooddigis] = digis_view.toa()[i];
        cm[ngooddigis] = digis_view.cm()[i];
        flags[ngooddigis] = digis_view.flags()[i];
        channel[ngooddigis] = denseIndexInfo_view.chNumber()[i];
        fedId[ngooddigis] = denseIndexInfo_view.fedId()[i];
        fedReadoutSeq[ngooddigis] = denseIndexInfo_view.fedReadoutSeq()[i];
        uint32_t cellInfoIdx = denseIndexInfo_view.cellInfoIdx()[i];
        chType[ngooddigis] = cellInfo_view.t()[cellInfoIdx];
        chI1[ngooddigis] = cellInfo_view.i1()[cellInfoIdx];
        chI2[ngooddigis] = cellInfo_view.i2()[cellInfoIdx];
        uint32_t modInfoIdx = denseIndexInfo_view.modInfoIdx()[i];
        isSiPM[ngooddigis] = moduleInfo_view.isSiPM()[modInfoIdx];
        modI1[ngooddigis] = moduleInfo_view.i1()[modInfoIdx];
        modI2[ngooddigis] = moduleInfo_view.i2()[modInfoIdx];

        ngooddigis++;
      }

      auto outdigi = std::make_unique<nanoaod::FlatTable>(ngooddigis, "HGCDigi", false);
      outdigi->setDoc("HGC DIGIS");

      tctp.resize(ngooddigis);
      adc.resize(ngooddigis);
      adcm1.resize(ngooddigis);
      tot.resize(ngooddigis);
      toa.resize(ngooddigis);
      cm.resize(ngooddigis);
      flags.resize(ngooddigis);
      channel.resize(ngooddigis);
      fedId.resize(ngooddigis);
      fedReadoutSeq.resize(ngooddigis);
      chType.resize(ngooddigis);
      chI1.resize(ngooddigis);
      chI2.resize(ngooddigis);
      isSiPM.resize(ngooddigis);
      modI1.resize(ngooddigis);
      modI2.resize(ngooddigis);

      outdigi->addColumn<uint16_t>("tctp", tctp, "Tc/Tp flags (2b)");
      outdigi->addColumn<uint16_t>("adc", adc, "adc measurement");
      outdigi->addColumn<uint16_t>("adcm1", adcm1, "adc measurement in BX-1");
      outdigi->addColumn<uint16_t>("tot", tot, "tot measurement");
      outdigi->addColumn<uint16_t>("toa", toa, "toa measurement");
      outdigi->addColumn<uint16_t>("cm", cm, "common mode sum");
      outdigi->addColumn<uint16_t>("flags", flags, "unpacking quality flags");
      outdigi->addColumn<int>("chType", chType, "channel type");
      outdigi->addColumn<uint16_t>("channel", channel, "sequential channel counting := (chip*2+half)*37 + 1/2 channel");
      outdigi->addColumn<bool>("isSiPM", isSiPM, "is tileboard or wafer");
      outdigi->addColumn<int>("modI1", modI1, "Si wafer U or tileboard iring coordinate");
      outdigi->addColumn<int>("modI2", modI2, "Si wafer V or tileboard iphi coordinate");
      outdigi->addColumn<int>("chI1", chI1, "Si channel U or tile iring coordinate");
      outdigi->addColumn<int>("chI2", chI2, "Si channel V or tile iphi coordinate");
      outdigi->addColumn<uint16_t>("fedId", fedId, "FED index");
      outdigi->addColumn<uint16_t>("fedReadoutSeq", fedReadoutSeq, "ECON-D index in FED readout sequence");

      iEvent.put(std::move(outdigi), "HGCDigi");
    }

    //rechit flattable
    if(!skipRecHits_) {
      
      // tempo: add digis_view for DIGI_FLAG
      const auto& digis = iEvent.get(digisToken_);
      auto const& digis_view = digis.const_view();

      //retrieve rechits and ensure size matches that of dense indices
      const auto& rechits = iEvent.get(rechitsToken_);
      auto const& rechits_view = rechits.const_view();
      int32_t nrechits = rechits_view.metadata().size();
  
      //all SoA must match in size otherwise we are in trouble
      assert(nrechits == ndenseIndices);

      //auto outhit = std::make_unique<nanoaod::FlatTable>(nrechits, "HGCHit", false);
      //outhit->setDoc("HGC RecHits");
      std::vector<double> energy(nrechits), time(nrechits);
      std::vector<float> x(nrechits), y(nrechits);
      std::vector<int> layer(nrechits);
      std::vector<uint16_t> rechitflags(nrechits);
      std::vector<bool> zSide(nrechits);

      // tempo: use DIGI_FLAG ---> will be changed to RECHIT_FLAG once produced in Calibration step
      int ngoodrechits = 0;
      for (int32_t i = 0; i < nrechits; i++) {
        if (digis_view.flags()[i] == hgcal::DIGI_FLAG::NotAvailable) continue;
        energy[ngoodrechits] = rechits_view.energy()[i];
        time[ngoodrechits] = rechits_view.time()[i];
        x[ngoodrechits] = denseIndexInfo_view.z()[i];
        y[ngoodrechits] = denseIndexInfo_view.y()[i];
        HGCalDetId detId(denseIndexInfo_view.detid()[i]);
        layer[ngoodrechits] = detId.layer();
        zSide[ngoodrechits] = detId.zside();

        ngoodrechits++;
      }

      auto outhit = std::make_unique<nanoaod::FlatTable>(ngoodrechits, "HGCHit", false);
      outhit->setDoc("HGC RecHits");

      energy.resize(ngoodrechits);
      time.resize(ngoodrechits);
      x.resize(ngoodrechits);
      y.resize(ngoodrechits);
      layer.resize(ngoodrechits);
      zSide.resize(ngoodrechits);      

      outhit->addColumn<double>("energy", energy, "calibrated energy");
      outhit->addColumn<double>("time", time, "time");
      outhit->addColumn<uint16_t>("flags", rechitflags, "rec hit quality flags");
      outhit->addColumn<int>("layer", layer, "layer");
      outhit->addColumn<float>("x", x, "x coordinate from geometry");
      outhit->addColumn<float>("y", y, "y coordinate from geometry");
      outhit->addColumn<bool>("zSide", zSide, "z side");
      iEvent.put(std::move(outhit), "HGCHit");
    }
  }

  void endStream() override {};

  void beginRun(edm::Run const& iRun, edm::EventSetup const& iSetup) override {}

  // ----------member data ---------------------------
  const edm::EDGetTokenT<HGCalTestSystemMetaData> metadataToken_;
  const edm::EDGetTokenT<hgcaldigi::HGCalDigiHost> digisToken_;
  const edm::EDGetTokenT<hgcalrechit::HGCalRecHitHost> rechitsToken_;
  edm::ESGetToken<hgcal::HGCalDenseIndexInfoHost, HGCalDenseIndexInfoRcd> denseIndexInfoTkn_;
  edm::ESGetToken<hgcal::HGCalMappingCellParamHost, HGCalElectronicsMappingRcd> cellTkn_;
  edm::ESGetToken<hgcal::HGCalMappingModuleParamHost, HGCalElectronicsMappingRcd> moduleTkn_;

  bool skipDigi_, skipRecHits_;
};

//define this as a plug-in
DEFINE_FWK_MODULE(HGCalNanoTableProducer);
