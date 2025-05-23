#include "DataFormats/FEDRawData/interface/FEDRawDataCollection.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/InputSourceDescription.h"
#include "FWCore/Framework/interface/InputSourceMacros.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/UnixSignalHandlers.h"
#include "EventFilter/Utilities/interface/GlobalEventNumber.h"
#include "HGCalCommissioning/SystemTestEventFilters/plugins/HGCalSlinkFromRawSource.h"
#include "EventFilter/Utilities/interface/SourceCommon.h"
#include "DataFormats/Provenance/interface/EventAuxiliary.h"
#include "DataFormats/Provenance/interface/EventID.h"
#include "DataFormats/Provenance/interface/Timestamp.h"
#include "EventFilter/Utilities/interface/crc32c.h"
#include <sys/time.h>

//
HGCalSlinkFromRawSource::HGCalSlinkFromRawSource(edm::ParameterSet const& pset, edm::InputSourceDescription const& desc)
    : edm::RawInputSource(pset, desc),
      daqProvenanceHelper_(edm::TypeID(typeid(FEDRawDataCollection))),
      trgProvenanceHelper_(edm::TypeID(typeid(FEDRawDataCollection))),
      metadataProvenanceHelper_(edm::TypeID(typeid(HGCalTestSystemMetaData))),
      eventID_(),
      processHistoryID_(),
      eventSkipperByID_(edm::EventSkipperByID::create(pset)) {
  //configure (starting) values to use for this run
  isRealData_ = pset.getUntrackedParameter<bool>("isRealData");
  runNumberVal_ = pset.getUntrackedParameter<unsigned>("runNumber");
  lumiSectionVal_ = pset.getUntrackedParameter<unsigned>("firstLumiSection");
  maxEventsPerLumiSection_ = pset.getUntrackedParameter<int>("maxEventsPerLumiSection");
  nEventsRead_ = 0;
  eventIdVal_ = 0;
  bxIdVal_ = 0;
  orbitIdVal_ = 0;
  useL1EventID_ = pset.getUntrackedParameter<bool>("useL1EventID");

  //init provenance helpers and run aux
  processHistoryID_ = metadataProvenanceHelper_.init(productRegistryUpdate(), processHistoryRegistryForUpdate());
  processHistoryID_ = trgProvenanceHelper_.init(productRegistryUpdate(), processHistoryRegistryForUpdate());
  processHistoryID_ = daqProvenanceHelper_.daqInit(productRegistryUpdate(), processHistoryRegistryForUpdate());
  setNewRun();
  setRunAuxiliary(
      new edm::RunAuxiliary(runNumberVal_, edm::Timestamp::beginOfTime(), edm::Timestamp::invalidTimestamp()));
  runAuxiliary()->setProcessHistoryID(processHistoryID_);

  //check that input files match the size of fed list
  fedIds_ = pset.getUntrackedParameter<std::vector<unsigned>>("fedIds");
  auto inputfiles = pset.getUntrackedParameter<std::vector<std::string>>("inputs");
  if (inputfiles.size() % fedIds_.size() != 0) {
    throw cms::Exception("[HGCalSlinkFromRawSource]")
        << "Number of inputs (" << inputfiles.size() << ") cannot be devided by the number of fedIds ("
        << fedIds_.size() << ")";
  }
  n_feds_scale_ = std::max(1U, pset.getUntrackedParameter<unsigned>("n_feds_scale", 1U));

  //build the file list to process
  std::vector<std::vector<std::string>> fileLists(fedIds_.size());
  for (unsigned i = 0; i < inputfiles.size(); ++i) {
    if (std::filesystem::exists(inputfiles[i])) {
      fileLists.at(i % fedIds_.size()).push_back(inputfiles[i]);
    }
  }

  //init the readers
  for (unsigned idx = 0; idx < fedIds_.size(); ++idx) {
    readers_[fedIds_[idx]] = std::make_shared<hgcal::SlinkFileReader>(fileLists[idx], fedIds_[idx]);
  }

  //special case for trigger inputs
  auto trig_inputs = pset.getUntrackedParameter<std::vector<std::string>>("trig_inputs", {});
  readers_[hgcal::SlinkFileReader::kTrigIdOffset] =
      std::make_shared<hgcal::SlinkFileReader>(trig_inputs, hgcal::SlinkFileReader::kTrigIdOffset);
  trig_num_blocks_ = pset.getUntrackedParameter<unsigned>("trig_num_blocks");
  trig_scintillator_block_id_ = pset.getUntrackedParameter<int>("trig_scintillator_block_id");
}

//
void HGCalSlinkFromRawSource::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.setComment("HGCAL file-based raw data source for CMSSW");
  desc.addUntracked<bool>("isRealData", true)->setComment("Name says it all");
  desc.addUntracked<unsigned>("runNumber", 1)->setComment("Run number to assign");
  desc.addUntracked<unsigned>("firstLumiSection", 1)->setComment("First lumi section to use");
  desc.addUntracked<int>("maxEventsPerLumiSection", -1)
      ->setComment("Use this metric to instantiate a new lumi section");
  desc.addUntracked<bool>("useL1EventID", true)
      ->setComment("Use L1 event ID from FED header if true or from TCDS FED if false");
  desc.addUntracked<std::vector<unsigned>>("fedIds", {0})->setComment("list of fedIds");
  desc.addUntracked<std::vector<std::string>>("inputs")->setComment("list of input files to use for DAQ");
  desc.addUntracked<std::vector<std::string>>("trig_inputs")->setComment("list of input files to use for TRIG");
  desc.addUntracked<unsigned>("trig_num_blocks", 6)->setComment("number of TDAQ blocks in the TRIG link");
  desc.addUntracked<int>("trig_scintillator_block_id", 5)
      ->setComment("index of the TDAQ block with scintillator TRIG info");
  desc.setAllowAnything();
  edm::EventSkipperByID::fillDescription(desc);
  descriptions.add("source", desc);
}

//
edm::RawInputSource::Next HGCalSlinkFromRawSource::checkNext() {
  bool status = updateRunAndEventInfo();

  //no valid event stop here
  if (!status || remainingEvents() == 0) {
    std::cout << "End of file or events required reached" << std::endl;
    resetLuminosityBlockAuxiliary();
    return Next::kStop;
  }

  //increment event counter and check if lumi-section should be changed
  nEventsRead_++;
  if (maxEventsPerLumiSection_ > 0 && nEventsRead_ > 1 && nEventsRead_ % maxEventsPerLumiSection_ == 0)
    lumiSectionVal_ += 1;

  //start new lumi block
  if (!luminosityBlockAuxiliary() || luminosityBlockAuxiliary()->luminosityBlock() != lumiSectionVal_) {
    timeval tv;
    gettimeofday(&tv, nullptr);
    const edm::Timestamp lsopentime((unsigned long long)tv.tv_sec * 1000000 + (unsigned long long)tv.tv_usec);
    edm::LuminosityBlockAuxiliary* lumiBlockAuxiliary = new edm::LuminosityBlockAuxiliary(
        runAuxiliary()->run(), lumiSectionVal_, lsopentime, edm::Timestamp::invalidTimestamp());
    setLuminosityBlockAuxiliary(lumiBlockAuxiliary);
    luminosityBlockAuxiliary()->setProcessHistoryID(processHistoryID_);
  }

  //flag new event is available
  setEventCached();
  return Next::kEvent;
}

//
void HGCalSlinkFromRawSource::read(edm::EventPrincipal& eventPrincipal) {
  if (!useL1EventID_)
    throw cms::Exception("HGCalSlinkFromRawSource::read") << "set L1EventId from TCDS block is not implemented";

  //build the event auxiliary quantities
  eventID_ = edm::EventID(runNumberVal_, lumiSectionVal_, eventIdVal_);

  edm::TimeValue_t time;
  timeval stv;
  gettimeofday(&stv, nullptr);
  time = stv.tv_sec;
  time = (time << 32) + stv.tv_usec;
  edm::Timestamp tstamp(time);

  edm::EventAuxiliary aux(eventID_,
                          processGUID(),
                          tstamp,
                          isRealData_,
                          edm::EventAuxiliary::PhysicsTrigger,
                          bxIdVal_,
                          edm::EventAuxiliary::invalidStoreNumber,
                          orbitIdVal_);
  aux.setProcessHistoryID(processHistoryID_);
  makeEvent(eventPrincipal, aux);

  std::unique_ptr<edm::WrapperBase> edp(new edm::Wrapper<FEDRawDataCollection>(std::move(rawData_)));
  eventPrincipal.put(daqProvenanceHelper_.productDescription(), std::move(edp), daqProvenanceHelper_.dummyProvenance());

  std::unique_ptr<edm::WrapperBase> trgedp(new edm::Wrapper<FEDRawDataCollection>(std::move(trgRawData_)));
  eventPrincipal.put(
      trgProvenanceHelper_.productDescription(), std::move(trgedp), trgProvenanceHelper_.dummyProvenance());

  std::unique_ptr<edm::WrapperBase> emd(new edm::Wrapper<HGCalTestSystemMetaData>(std::move(metaData_)));
  eventPrincipal.put(
      metadataProvenanceHelper_.productDescription(), std::move(emd), metadataProvenanceHelper_.dummyProvenance());
}

//
bool HGCalSlinkFromRawSource::updateRunAndEventInfo() {
  rawData_ = std::make_unique<FEDRawDataCollection>();
  trgRawData_ = std::make_unique<FEDRawDataCollection>();
  metaData_ = std::make_unique<HGCalTestSystemMetaData>();

  auto copyToFEDRawData =
      [](FEDRawDataCollection& rawData, const hgcal_slinkfromraw::RecordRunning* rEvent, unsigned fedId) {
        using T = FEDRawData::Data::value_type;
        const auto size = sizeof(uint64_t) / sizeof(T) * (rEvent->payloadLength());
        auto& fed_data = rawData.FEDData(fedId);
        fed_data.resize(size);
        memcpy(fed_data.data(), reinterpret_cast<const T*>(rEvent->payload()), size);
      };

  bool eventRead = false;
  while (!eventRead) {
    // read DAQ Slinks
    for (unsigned idx = 0; idx < fedIds_.size(); ++idx) {
      const auto& fedId = fedIds_[idx];
      auto reader = readers_.at(fedId);
      auto rEvent = reader->nextEvent();
      if (!rEvent) {
        return false;
      }

      if (idx == 0) {
        eventIdVal_ = rEvent->slinkBoe()->eventId();
        bxIdVal_ = rEvent->slinkEoe()->bxId();
        orbitIdVal_ = rEvent->slinkEoe()->orbitId();

        if (eventSkipperByID_) {
          if (eventSkipperByID_->skipIt(runNumberVal_, lumiSectionVal_, eventIdVal_)) {
            break;  // break the for loop (on fedIds)
          }
        }
        eventRead = true;
        for (unsigned icopy = 0; icopy < n_feds_scale_; ++icopy) {
          copyToFEDRawData(*rawData_, rEvent, icopy * fedIds_.size() + fedId);
        }
      } else {
        // find the event matched to the first slink
        while (rEvent) {
          if (rEvent->slinkBoe()->eventId() == eventIdVal_ && rEvent->slinkEoe()->bxId() == bxIdVal_ &&
              rEvent->slinkEoe()->orbitId() == orbitIdVal_) {
            for (unsigned icopy = 0; icopy < n_feds_scale_; ++icopy) {
              copyToFEDRawData(*rawData_, rEvent, icopy * fedIds_.size() + fedId);
            }
            break;
          } else {
            edm::LogError("HGCalSlinkFromRawSource")
                << "Mismatch in E/B/O counters for fedId=" << fedId << ": expect eventId=" << eventIdVal_
                << ", bxId=" << bxIdVal_ << ", orbitId=" << orbitIdVal_
                << ", got eventId = " << rEvent->slinkBoe()->eventId() << ", bxId = " << rEvent->slinkEoe()->bxId()
                << ", orbitId=" << rEvent->slinkEoe()->orbitId();
            if (rEvent->slinkBoe()->eventId() < eventIdVal_) {
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

      if (eventRead) {
        while (rTrgEvent) {
          // find the trigger event matched to the first DAQ slink
          bool evMatches(rTrgEvent->slinkBoe()->eventId() == eventIdVal_);
          bool bxMatches(rTrgEvent->slinkEoe()->bxId() == bxIdVal_);
          bool orbitMatches(rTrgEvent->slinkEoe()->orbitId() == orbitIdVal_);
          metaData_->setTrigBlockFlags((!evMatches) * HGCalTestSystemMetaData::TestSystemMetaDataFlags::EVMISMATCH +
                                       (!bxMatches) * HGCalTestSystemMetaData::TestSystemMetaDataFlags::BXMISMATCH +
                                       (!orbitMatches) *
                                           HGCalTestSystemMetaData::TestSystemMetaDataFlags::ORBITMISMATCH);
          if (evMatches && bxMatches && orbitMatches) {
            reader->readTriggerData(*metaData_, rTrgEvent, trig_num_blocks_, trig_scintillator_block_id_);
            metaData_->setTrigBlockFlags(HGCalTestSystemMetaData::TestSystemMetaDataFlags::VALID);
            break;
          } else {
            LogDebug("SlinkFromRaw") << "Mismatch in E/B/O counters for the trigger link"
                                     << ": expect eventId=" << eventIdVal_ << ", bxId=" << bxIdVal_
                                     << ", orbitId=" << orbitIdVal_
                                     << ", got eventId = " << rTrgEvent->slinkBoe()->eventId()
                                     << ", bxId = " << rTrgEvent->slinkEoe()->bxId()
                                     << ", orbitId=" << rTrgEvent->slinkEoe()->orbitId();
            if (rTrgEvent->slinkBoe()->eventId() < eventIdVal_) {
              rTrgEvent = reader->nextEvent();
              continue;
            } else {
              break;
            }
          }
        }
      }
    }  //end read trigger Slink
  }  //end event read

  return true;
}

DEFINE_FWK_INPUT_SOURCE(HGCalSlinkFromRawSource);
