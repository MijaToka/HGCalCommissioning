#ifndef HGCalCommissioning_SystemTestEventFilters_HGCalSlinkFromRawSource_h
#define HGCalCommissioning_SystemTestEventFilters_HGCalSlinkFromRawSource_h

#include "DataFormats/FEDRawData/interface/FEDRawDataCollection.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Sources/interface/ProducerSourceFromFiles.h"

#include "../interface/HGCalSlinkFileReader.h"

class HGCalSlinkFromRawSource : public edm::ProducerSourceFromFiles {
public:
  HGCalSlinkFromRawSource(edm::ParameterSet const &pset, edm::InputSourceDescription const &desc);

private:
  bool setRunAndEventInfo(edm::EventID &id,
                          edm::TimeValue_t &theTime,
                          edm::EventAuxiliary::ExperimentType &eType) override;
  void produce(edm::Event &e) override;

private:
  std::vector<unsigned> fedIds_;
  std::map<unsigned, std::shared_ptr<hgcal::SlinkFileReader>> readers_;

  std::unique_ptr<FEDRawDataCollection> rawData_;
  std::unique_ptr<HGCalTestSystemMetaData> metaData_;
};

#endif
