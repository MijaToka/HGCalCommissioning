// Author: Izaak Neutelings (August 2024)
// Based on https://github.com/CMS-HGCAL/cmssw/blob/dev/hackathon_base_CMSSW_14_1_X/EventFilter/HGCalRawToDigi/plugins/HGCalRawToDigi.cc
#include <memory>
#include <algorithm> // for std::min
#include <string> // for std::string, std::to_string()

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/ESWatcher.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/StreamID.h"

#include "DataFormats/FEDRawData/interface/FEDRawDataCollection.h"
#include "DataFormats/HGCalDigi/interface/HGCalDigiHost.h"
#include "DataFormats/HGCalDigi/interface/HGCalECONDPacketInfoHost.h"
#include "DataFormats/HGCalDigi/interface/HGCalRawDataDefinitions.h"

#include "CondFormats/DataRecord/interface/HGCalElectronicsMappingRcd.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingModuleIndexer.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingCellIndexer.h"
#include "CondFormats/DataRecord/interface/HGCalModuleConfigurationRcd.h"
#include "CondFormats/HGCalObjects/interface/HGCalConfiguration.h"

#include "EventFilter/HGCalRawToDigi/interface/HGCalUnpacker.h"

class TestHGCalRawToDigi : public edm::stream::EDProducer<> {
public:
  explicit TestHGCalRawToDigi(const edm::ParameterSet&);

  static void fillDescriptions(edm::ConfigurationDescriptions&);

private:
  void produce(edm::Event&, const edm::EventSetup&) override;
  void beginRun(edm::Run const&, edm::EventSetup const&) override;
  void endRun(edm::Run const&, edm::EventSetup const&) override;

  // input tokens
  const edm::EDGetTokenT<FEDRawDataCollection> fedRawToken_;

  // output tokens
  const edm::EDPutTokenT<hgcaldigi::HGCalDigiHost> digisToken_;
  const edm::EDPutTokenT<hgcaldigi::HGCalECONDPacketInfoHost> econdPacketInfoToken_;

  // config tokens and objects
  edm::ESWatcher<HGCalElectronicsMappingRcd> mapWatcher_;
  edm::ESGetToken<HGCalMappingCellIndexer, HGCalElectronicsMappingRcd> cellIndexToken_;
  edm::ESGetToken<HGCalMappingModuleIndexer, HGCalElectronicsMappingRcd> moduleIndexToken_;
  edm::ESGetToken<HGCalConfiguration, HGCalModuleConfigurationRcd> configToken_; 
  HGCalMappingCellIndexer cellIndexer_;
  HGCalMappingModuleIndexer moduleIndexer_;
  HGCalConfiguration config_;
  HGCalUnpacker unpacker_;
  std::map<uint32_t, std::vector<uint32_t> > aveadc_map_;
};

TestHGCalRawToDigi::TestHGCalRawToDigi(const edm::ParameterSet& iConfig)
    : fedRawToken_(consumes<FEDRawDataCollection>(iConfig.getParameter<edm::InputTag>("src"))),
      digisToken_(produces<hgcaldigi::HGCalDigiHost>()),
      econdPacketInfoToken_(produces<hgcaldigi::HGCalECONDPacketInfoHost>()),
      cellIndexToken_(esConsumes<edm::Transition::BeginRun>()),
      moduleIndexToken_(esConsumes<edm::Transition::BeginRun>()),
      configToken_(esConsumes<edm::Transition::BeginRun>()) { }

void TestHGCalRawToDigi::beginRun(edm::Run const& iRun, edm::EventSetup const& iSetup) {
  if (mapWatcher_.check(iSetup)) {
    moduleIndexer_ = iSetup.getData(moduleIndexToken_);
    cellIndexer_ = iSetup.getData(cellIndexToken_);
    config_ = iSetup.getData(configToken_);
  }
}

void TestHGCalRawToDigi::endRun(edm::Run const& iRun, edm::EventSetup const& iSetup) {
  std::cout << ">>> TestHGCalRawToDigi::endRun: " << std::endl;
  std::cout << "  Dense indices  |  ADC averaged over channels" << std::endl;
  std::cout << "  fed econd  eRx |";
  std::size_t nevts = std::min(20,int(aveadc_map_[0].size()));
  for (std::size_t i = 0; i < nevts; ++i) {
    std::cout << std::setw(6) << ("evt" + std::to_string(i+1));
  }
  std::cout << std::endl;
  for (unsigned fedId = 0; fedId < moduleIndexer_.fedCount(); ++fedId) {
    const auto econdMax = moduleIndexer_.getMaxModuleSize(fedId);
    for (uint32_t econdIdx = 0; econdIdx < econdMax; econdIdx++) {
      const auto erxMax = moduleIndexer_.getMaxERxSize(fedId,econdIdx);
      for (uint32_t erxIdx = 0; erxIdx < erxMax; erxIdx++) {
        uint32_t eRxDenseIdx = moduleIndexer_.getIndexForModuleErx(fedId, econdIdx, erxIdx);
        std::cout << std::setw(5) << fedId << std::setw(6) << econdIdx << std::setw(5) << erxIdx << " |";
        for (std::size_t i = 0; i < nevts; ++i) {
          std::cout << std::setw(6) << aveadc_map_[eRxDenseIdx][i];
        }
        std::cout << std::endl;
      } // close loop over eRx ROCs
    } // close loop over ECON-Ds
  } // close loop over FEDs
}

void TestHGCalRawToDigi::produce(edm::Event& iEvent, const edm::EventSetup& iSetup) {
  std::cout << ">>> TestHGCalRawToDigi: Event " << iEvent.id()
            << " ========================================================================================" << std::endl;
  hgcaldigi::HGCalDigiHost digis(moduleIndexer_.getMaxDataSize(), cms::alpakatools::host());
  hgcaldigi::HGCalECONDPacketInfoHost econdPacketInfo(moduleIndexer_.getMaxModuleSize(), cms::alpakatools::host());
  
  // CREATE DIGIs
  // std::cout << "Created DIGIs SOA with " << digis.view().metadata().size() << " entries" << std::endl;
  const auto& raw_data = iEvent.get(fedRawToken_);
  for (unsigned fedId = 0; fedId < moduleIndexer_.fedCount(); ++fedId) {
    const auto& fed_data = raw_data.FEDData(fedId);
    if (fed_data.size() == 0)
      continue;
    unpacker_.parseFEDData(fedId, fed_data, moduleIndexer_, config_, digis, econdPacketInfo, /*headerOnlyMode*/ false);
  }
  
  // CHECK DIGIs
  for (unsigned fedId = 0; fedId < moduleIndexer_.fedCount(); ++fedId) {
    //std::cout << "fed=" << fedId << std::endl;
    const auto econdMax = moduleIndexer_.getMaxModuleSize(fedId);
    for (uint32_t econdIdx = 0; econdIdx < econdMax; econdIdx++) {
      //std::cout << "fed=" << fedId << ", econdIdx=" << econdIdx << std::endl;
      const auto erxMax = moduleIndexer_.getMaxERxSize(fedId,econdIdx);
      std::cout << "   fed econd   eRx  chan |  tctp adcm1   adc   tot   toa    cm  flags" << std::endl;
      for (uint32_t erxIdx = 0; erxIdx < erxMax; erxIdx++) {
        uint32_t eRxDenseIdx = moduleIndexer_.getIndexForModuleErx(fedId, econdIdx, erxIdx);
        std::cout << "   erxIdx=" << erxIdx << ", eRxDenseIdx=" << eRxDenseIdx << std::endl;
        uint32_t aveadc = 0, nchans = 0; // averaged over channels
        for (uint32_t channelIdx = 0; channelIdx < HGCalMappingCellIndexer::maxChPerErx_; channelIdx++) {
          uint32_t denseIdx = moduleIndexer_.getIndexForModuleData(fedId, econdIdx, erxIdx, channelIdx);
          if(digis.view()[denseIdx].flags()!=hgcal::DIGI_FLAG::NotAvailable) {
            aveadc += digis.view()[denseIdx].adc();
            nchans++;
          }
          //std::cout << ">>> HGCalUnpacker:    channelIdx= " << channelIdx << ", denseIdx = " << denseIdx
          //          << ", ADC=" << adc << std::endl;
          std::cout << std::dec << std::setfill(' ')
                    << std::setw(6) << fedId << std::setw(6) << econdIdx
                    << std::setw(6) << erxIdx << std::setw(6) << channelIdx << " |"
                    << std::setw(6) << (uint32_t) digis.view()[denseIdx].tctp()
                    << std::setw(6) << digis.view()[denseIdx].adcm1() << std::setw(6) << digis.view()[denseIdx].adc()
                    << std::setw(6) << digis.view()[denseIdx].tot()   << std::setw(6) << digis.view()[denseIdx].toa() 
                    << std::setw(6) << digis.view()[denseIdx].cm()
                    << " 0x" << std::hex << std::setfill('0') << std::setw(4) << digis.view()[denseIdx].flags()
                    << std::dec << std::setfill(' ') << std::endl;
        }
        aveadc *= 1./nchans; //HGCalMappingCellIndexer::maxChPerErx_;
        //if (aveadc_map_.find(eRxDenseIdx)!=aveadc_map_.end())
        //  aveadc_map_[eRxDenseIdx] = { };
        aveadc_map_[eRxDenseIdx].push_back(aveadc);
      } // close loop over eRx ROCs
    } // close loop over ECON-Ds
  } // close loop over FEDs
  
}

// fill descriptions
void TestHGCalRawToDigi::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("src", edm::InputTag("rawDataCollector"));
  desc.add<std::vector<unsigned int> >("fedIds", {});
  descriptions.add("hgcalDigis", desc);
}

// define this as a plug-in
DEFINE_FWK_MODULE(TestHGCalRawToDigi);
