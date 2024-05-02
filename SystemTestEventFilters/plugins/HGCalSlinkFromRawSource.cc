#include "HGCalSlinkFromRawSource.h"

#include "FWCore/Framework/interface/InputSourceMacros.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/Utilities/interface/Exception.h"

#include <ostream>
#include <iostream>
#include <fstream>
#include <filesystem>

HGCalSlinkFromRawSource::HGCalSlinkFromRawSource(edm::ParameterSet const& pset, edm::InputSourceDescription const& desc)
    : ProducerSourceFromFiles(pset, desc, true), fedIds_(pset.getUntrackedParameter<std::vector<unsigned>>("fedIds")) {
  auto inputfiles = pset.getUntrackedParameter<std::vector<std::string>>("inputs");
  if (inputfiles.size() % fedIds_.size() != 0) {
    throw cms::Exception("[HGCalSlinkFromRawSource]")
        << "Number of inputs (" << inputfiles.size() << ") cannot be devided by the number of fedIds ("
        << fedIds_.size() << ")";
  }

  std::vector<std::vector<std::string>> fileLists(fedIds_.size());
  for (unsigned i = 0; i < inputfiles.size(); ++i) {
    if (std::filesystem::exists(inputfiles[i])) {
      fileLists.at(i % fedIds_.size()).push_back(inputfiles[i]);
    }
  }

  for (unsigned idx = 0; idx < fedIds_.size(); ++idx) {
    readers_[fedIds_[idx]] = std::make_shared<hgcal::SlinkFileReader>(fileLists[idx], fedIds_[idx]);
  }

  auto trig_inputs = pset.getUntrackedParameter<std::vector<std::string>>("trig_inputs", {});
  readers_[hgcal::SlinkFileReader::kTrigIdOffset] =
      std::make_shared<hgcal::SlinkFileReader>(trig_inputs, hgcal::SlinkFileReader::kTrigIdOffset);

  produces<FEDRawDataCollection>();
  produces<HGCalTestSystemMetaData>();
}

bool HGCalSlinkFromRawSource::setRunAndEventInfo(edm::EventID& id,
                                                 edm::TimeValue_t& theTime,
                                                 edm::EventAuxiliary::ExperimentType& eType) {
  rawData_ = std::make_unique<FEDRawDataCollection>();
  metaData_ = std::make_unique<HGCalTestSystemMetaData>();

  auto copyToFEDRawData =
      [](FEDRawDataCollection& rawData, const hgcal_slinkfromraw::RecordRunning* rEvent, unsigned fedId) {
        using T = FEDRawData::Data::value_type;
        const auto size = sizeof(uint64_t) / sizeof(T) * (rEvent->payloadLength());
        auto& fed_data = rawData.FEDData(fedId);
        fed_data.resize(size);
        memcpy(fed_data.data(), reinterpret_cast<const T*>(rEvent->payload()), size);
      };

  uint64_t eventId_ = 0;
  uint16_t bxId_ = 0;
  uint32_t orbitId_ = 0;

  // read DAQ Slinks
  for (unsigned idx = 0; idx < fedIds_.size(); ++idx) {
    const auto& fedId = fedIds_[idx];
    auto reader = readers_.at(fedId);
    auto rEvent = reader->nextEvent();
    if (!rEvent) {
      return false;
    }

    if (idx == 0) {
      eventId_ = rEvent->slinkBoe()->eventId();
      bxId_ = rEvent->slinkEoe()->bxId();
      orbitId_ = rEvent->slinkEoe()->orbitId();
      copyToFEDRawData(*rawData_, rEvent, fedId);
    } else {
      // find the event matched to the first slink
      while (rEvent) {
        if (rEvent->slinkBoe()->eventId() == eventId_ && rEvent->slinkEoe()->bxId() == bxId_ &&
            rEvent->slinkEoe()->orbitId() == orbitId_) {
          copyToFEDRawData(*rawData_, rEvent, fedId);
          break;
        } else {
          edm::LogError("HGCalSlinkFromRawSource")
              << "Mismatch in E/B/O counters for fedId=" << fedId << ": expect eventId=" << eventId_
              << ", bxId=" << bxId_ << ", orbitId=" << orbitId_ << ", got eventId = " << rEvent->slinkBoe()->eventId()
              << ", bxId = " << rEvent->slinkEoe()->bxId() << ", orbitId=" << rEvent->slinkEoe()->orbitId();
          if (rEvent->slinkBoe()->eventId() < eventId_) {
            rEvent = reader->nextEvent();
            continue;
          } else {
            break;
          }
        }
      }
    }
  }

  // read trigger Slink
  {
    auto reader = readers_.at(hgcal::SlinkFileReader::kTrigIdOffset);

    // rTrgEvent will be null if there are no trig_inputs
    auto rTrgEvent = reader->nextEvent();

    while (rTrgEvent) {
      // find the trigger event matched to the first DAQ slink
      if (rTrgEvent->slinkBoe()->eventId() == eventId_ && rTrgEvent->slinkEoe()->bxId() == bxId_ &&
          rTrgEvent->slinkEoe()->orbitId() == orbitId_) {
        reader->readTriggerData(*metaData_, rTrgEvent);
        break;
      } else {
        edm::LogError("SlinkFromRaw") << "Mismatch in E/B/O counters for the trigger link"
                                      << ": expect eventId=" << eventId_ << ", bxId=" << bxId_
                                      << ", orbitId=" << orbitId_
                                      << ", got eventId = " << rTrgEvent->slinkBoe()->eventId()
                                      << ", bxId = " << rTrgEvent->slinkEoe()->bxId()
                                      << ", orbitId=" << rTrgEvent->slinkEoe()->orbitId();
        if (rTrgEvent->slinkBoe()->eventId() < eventId_) {
          rTrgEvent = reader->nextEvent();
          continue;
        } else {
          break;
        }
      }
    }
  }

  return true;
}

void HGCalSlinkFromRawSource::produce(edm::Event& e) {
  e.put(std::move(rawData_));
  e.put(std::move(metaData_));
}

DEFINE_FWK_INPUT_SOURCE(HGCalSlinkFromRawSource);
