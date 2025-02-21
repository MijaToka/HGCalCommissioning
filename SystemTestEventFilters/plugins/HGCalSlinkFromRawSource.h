#ifndef HGCalCommissioning_SystemTestEventFilters_HGCalSlinkFromRawSource_h
#define HGCalCommissioning_SystemTestEventFilters_HGCalSlinkFromRawSource_h

#include <condition_variable>
#include <cstdio>
#include <filesystem>
#include <memory>
#include <mutex>
#include <thread>
#include <random>
#include <algorithm>

#include "oneapi/tbb/concurrent_queue.h"
#include "oneapi/tbb/concurrent_vector.h"
#include "DataFormats/Provenance/interface/Timestamp.h"
#include "FWCore/Sources/interface/RawInputSource.h"
#include "FWCore/Framework/interface/EventPrincipal.h"
#include "FWCore/Sources/interface/DaqProvenanceHelper.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "FWCore/Sources/interface/EventSkipperByID.h"

#include "DataFormats/FEDRawData/interface/FEDRawDataCollection.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "HGCalCommissioning/SystemTestEventFilters/interface/HGCalSlinkFileReader.h"
#include "HGCalCommissioning/SystemTestEventFilters/interface/HGCalMetaDataProvenanceHelper.h"
#include "HGCalCommissioning/SystemTestEventFilters/interface/HGCalTrgDataProvenanceHelper.h"

class InputSourceDescription;
class ParameterSet;

/**
  @short source to put FEDRawData and metadata after parsing system test binary files
 */
class HGCalSlinkFromRawSource : public edm::RawInputSource {
public:
  explicit HGCalSlinkFromRawSource(edm::ParameterSet const&, edm::InputSourceDescription const&);
  ~HGCalSlinkFromRawSource() override {}
  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

protected:
  Next checkNext() override;
  void read(edm::EventPrincipal& eventPrincipal) override;

private:
  bool updateRunAndEventInfo();

  bool isRealData_;
  uint32_t runNumberVal_, lumiSectionVal_;
  uint64_t eventIdVal_, bxIdVal_, orbitIdVal_;
  int maxEventsPerLumiSection_;
  uint64_t nEventsRead_;
  bool useL1EventID_;
  std::vector<unsigned> fedIds_;
  unsigned n_feds_scale_;
  unsigned trig_num_blocks_;
  int trig_scintillator_block_id_;

  const edm::DaqProvenanceHelper daqProvenanceHelper_;
  const HGCalTrgDataProvenanceHelper trgProvenanceHelper_;
  const HGCalMetaDataProvenanceHelper metadataProvenanceHelper_;
  edm::EventID eventID_;
  edm::ProcessHistoryID processHistoryID_;
  std::unique_ptr<edm::EventSkipperByID> eventSkipperByID_;

  std::map<unsigned, std::shared_ptr<hgcal::SlinkFileReader>> readers_;
  std::unique_ptr<FEDRawDataCollection> rawData_, trgRawData_;
  std::unique_ptr<HGCalTestSystemMetaData> metaData_;
};

#endif  // HGCalCommissioning_SystemTestEventFilters_HGCalSlinkFromRawSource_h
