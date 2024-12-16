#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/ESWatcher.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/StreamID.h"

#include "DataFormats/FEDRawData/interface/FEDRawDataCollection.h"
#include "DataFormats/HGCalDigi/interface/HGCalDigiHost.h"
#include "DataFormats/HGCalDigi/interface/HGCalECONDPacketInfoHost.h"

#include "CondFormats/HGCalObjects/interface/HGCalMappingModuleIndexer.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingCellIndexer.h"
#include "CondFormats/DataRecord/interface/HGCalModuleConfigurationRcd.h"
#include "CondFormats/HGCalObjects/interface/HGCalConfiguration.h"

#include "EventFilter/HGCalRawToDigi/interface/HGCalUnpacker.h"

#include "HGCalCommissioning/HGCalDigiTrigger/interface/HGCalDigiTriggerHost.h"
#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalUnpackerTrigger.h"
#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalModuleIndexerTrigger.h"

class HGCalRawToDigiTrigger : public edm::stream::EDProducer<> {
  // TODO: this should also probably be split between DAQ and Trigger, and two producers should be created in the python config

public:
  explicit HGCalRawToDigiTrigger(const edm::ParameterSet&);

  static void fillDescriptions(edm::ConfigurationDescriptions&);

private:
  void produce(edm::Event&, const edm::EventSetup&) override;
  void beginRun(edm::Run const&, edm::EventSetup const&) override;

  // input tokens
  const edm::EDGetTokenT<FEDRawDataCollection> fedRawToken_;
  const edm::EDGetTokenT<FEDRawDataCollection> fedRawTriggerToken_;

  // output tokens
  const edm::EDPutTokenT<hgcaldigi::HGCalDigiHost> digisDAQToken_;
  const edm::EDPutTokenT<hgcaldigi::HGCalECONDPacketInfoHost> econdPacketInfoDAQToken_;
  const edm::EDPutTokenT<hgcaldigi::HGCalDigiTriggerHost> digisTriggerToken_;

  // TODO @hqucms
  // what else do we want to output?

  // config tokens and objects
  edm::ESWatcher<HGCalElectronicsMappingRcd> mapWatcher_;
  edm::ESGetToken<HGCalMappingCellIndexer, HGCalElectronicsMappingRcd> cellIndexToken_;
  edm::ESGetToken<HGCalMappingModuleIndexer, HGCalElectronicsMappingRcd> moduleIndexToken_;
  edm::ESGetToken<HGCalConfiguration, HGCalModuleConfigurationRcd> configToken_;
  HGCalMappingCellIndexer cellIndexer_;
  HGCalMappingModuleIndexer moduleIndexer_;
  HGCalConfiguration config_;
  HGCalModuleIndexerTrigger moduleIndexerTrigger_;

  // TODO @hqucms
  // how to implement this enabled eRx pattern? Can this be taken from the logical mapping?
  // HGCalCondSerializableModuleInfo::ERxBitPatternMap erxEnableBits_;
  // std::map<uint16_t, uint16_t> fed2slink_;

  // TODO @hqucms
  // HGCalUnpackerConfig unpackerConfig_;
  HGCalUnpacker unpacker_;
  HGCalUnpackerTrigger unpacker_trigger_;
  std::string unpacking_configuration_;

  const bool fixCalibChannel_;
};

HGCalRawToDigiTrigger::HGCalRawToDigiTrigger(const edm::ParameterSet& iConfig)
    : fedRawToken_(consumes<FEDRawDataCollection>(iConfig.getParameter<edm::InputTag>("src"))),
      fedRawTriggerToken_(consumes<FEDRawDataCollection>(iConfig.getParameter<edm::InputTag>("src_trigger"))),
      digisDAQToken_(produces<hgcaldigi::HGCalDigiHost>()),
      econdPacketInfoDAQToken_(produces<hgcaldigi::HGCalECONDPacketInfoHost>()),
      digisTriggerToken_(produces<hgcaldigi::HGCalDigiTriggerHost>("HGCalDigiTrigger")),
      cellIndexToken_(esConsumes<edm::Transition::BeginRun>()),
      moduleIndexToken_(esConsumes<edm::Transition::BeginRun>()),
      configToken_(esConsumes<edm::Transition::BeginRun>()),
      // unpackerConfig_(HGCalUnpackerConfig{.sLinkBOE = iConfig.getParameter<unsigned int>("slinkBOE"),
      //                                     .cbHeaderMarker = iConfig.getParameter<unsigned int>("cbHeaderMarker"),
      //                                     .econdHeaderMarker = iConfig.getParameter<unsigned int>("econdHeaderMarker"),
      //                                     .payloadLengthMax = iConfig.getParameter<unsigned int>("payloadLengthMax"),
      //                                     .applyFWworkaround = iConfig.getParameter<bool>("applyFWworkaround")}),
      unpacking_configuration_(iConfig.getParameter<std::string>("unpacking_configuration")),
      fixCalibChannel_(iConfig.getParameter<bool>("fixCalibChannel")) {}

void HGCalRawToDigiTrigger::beginRun(edm::Run const& iRun, edm::EventSetup const& iSetup) {
  // retrieve logical mapping
  if (mapWatcher_.check(iSetup)) {
    moduleIndexer_ = iSetup.getData(moduleIndexToken_);
    cellIndexer_ = iSetup.getData(cellIndexToken_);
    config_ = iSetup.getData(configToken_);
  }

  // TODO @hqucms
  // retrieve configs: TODO
  // auto moduleInfo = iSetup.getData(moduleInfoToken_);

  // TODO @hqucms
  // init unpacker with proper configs
}

void HGCalRawToDigiTrigger::produce(edm::Event& iEvent, const edm::EventSetup& iSetup) {
  hgcaldigi::HGCalDigiHost digisDAQ(moduleIndexer_.getMaxDataSize(), cms::alpakatools::host());
  hgcaldigi::HGCalECONDPacketInfoHost econdPacketInfoDAQ(moduleIndexer_.getMaxModuleSize(), cms::alpakatools::host());

  moduleIndexerTrigger_.setLayerOffset(1000);
  moduleIndexerTrigger_.setModOffset(100);
  moduleIndexerTrigger_.setMaxLayer(10);
  moduleIndexerTrigger_.setMaxMod(10);
  moduleIndexerTrigger_.setMaxCh(100);
  uint32_t maxIndexTrigger = moduleIndexerTrigger_.getMaxIndex();
  LogDebug("[HGCalRawToDigiTrigger]") << "maxIndexTrigger = " << maxIndexTrigger << std::endl;

  hgcaldigi::HGCalDigiTriggerHost digisTrigger(maxIndexTrigger, cms::alpakatools::host());
  LogDebug("[HGCalRawToDigiTrigger]") << "Created DIGIs SOA with " << digisTrigger.view().metadata().size()
                                      << " entries" << std::endl;

  // retrieve the FED raw data
  const auto& raw_data = iEvent.get(fedRawToken_);
  const auto& raw_data_trigger = iEvent.get(fedRawTriggerToken_);

  for (int32_t i = 0; i < digisDAQ.view().metadata().size(); i++) {
    digisDAQ.view()[i].flags() = hgcal::DIGI_FLAG::NotAvailable;
  }
  for (unsigned fedId = 0; fedId < moduleIndexer_.fedCount(); ++fedId) {
    const auto& fed_data = raw_data.FEDData(fedId);
    if (fed_data.size() == 0)
      continue;
    unpacker_.parseFEDData(
        fedId, fed_data, moduleIndexer_, config_, digisDAQ, econdPacketInfoDAQ, /*headerOnlyMode*/ false);
  }

  for (int32_t i = 0; i < digisTrigger.view().metadata().size(); i++) {
    digisTrigger.view()[i].flags() = hgcal::DIGI_FLAG::NotAvailable;
  }
  const auto& fed_data_trigger = raw_data_trigger.FEDData(0);
  if (fed_data_trigger.size() != 0)
    unpacker_trigger_.parseFEDData(
        fed_data_trigger, moduleIndexerTrigger_, config_, digisTrigger, unpacking_configuration_);

  iEvent.emplace(digisDAQToken_, std::move(digisDAQ));
  iEvent.emplace(econdPacketInfoDAQToken_, std::move(econdPacketInfoDAQ));
  iEvent.emplace(digisTriggerToken_, std::move(digisTrigger));
}

// fill descriptions
void HGCalRawToDigiTrigger::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("src", edm::InputTag("rawDataCollector"));
  desc.add<edm::InputTag>("src_trigger", edm::InputTag("trgRawDataCollector"));
  desc.add<std::string>("unpacking_configuration", "TBsep24");
  desc.add<std::vector<unsigned int> >("fedIds", {});
  desc.add<bool>("fixCalibChannel", true)
      ->setComment("FIXME: always treat calib channels in characterization mode; to be fixed in ROCv3b");
  descriptions.add("hgcalDigis", desc);
}

// define this as a plug-in
DEFINE_FWK_MODULE(HGCalRawToDigiTrigger);
