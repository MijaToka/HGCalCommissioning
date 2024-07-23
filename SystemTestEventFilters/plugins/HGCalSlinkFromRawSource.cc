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
      metadataProvenanceHelper_(edm::TypeID(typeid(HGCalTestSystemMetaData))),
      eventID_(),
      processHistoryID_() {

  //configure (starting) values to use for this run
  isRealData_=pset.getUntrackedParameter<bool>("isRealData");
  runNumberVal_=pset.getUntrackedParameter<unsigned>("runNumber");
  lumiSectionVal_=pset.getUntrackedParameter<unsigned>("firstLumiSection");
  maxEventsPerLumiSection_=pset.getUntrackedParameter<int>("maxEventsPerLumiSection");
  nEventsRead_=0;
  eventIdVal_=0;
  bxIdVal_=0;
  orbitIdVal_=0;
  useL1EventID_=pset.getUntrackedParameter<bool>("useL1EventID");

  //init provenance helpers and run aux
  processHistoryID_ = metadataProvenanceHelper_.init(productRegistryUpdate(), processHistoryRegistryForUpdate());
  processHistoryID_ = daqProvenanceHelper_.daqInit(productRegistryUpdate(), processHistoryRegistryForUpdate());
  setNewRun();
  setRunAuxiliary(new edm::RunAuxiliary(runNumberVal_, edm::Timestamp::beginOfTime(), edm::Timestamp::invalidTimestamp()));
  runAuxiliary()->setProcessHistoryID(processHistoryID_);


  //check that input files match the size of fed list
  fedIds_=pset.getUntrackedParameter<std::vector<unsigned>>("fedIds");
  auto inputfiles = pset.getUntrackedParameter<std::vector<std::string>>("inputs");
  if (inputfiles.size() % fedIds_.size() != 0) {
    throw cms::Exception("[HGCalSlinkFromRawSource]")
        << "Number of inputs (" << inputfiles.size() << ") cannot be devided by the number of fedIds ("
        << fedIds_.size() << ")";
  }
  
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
}

//
void HGCalSlinkFromRawSource::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.setComment("HGCAL file-based raw data source for CMSSW");
  desc.addUntracked<bool>("isRealData",true)->setComment("Name says it all");
  desc.addUntracked<unsigned>("runNumber",1)->setComment("Run number to assign");
  desc.addUntracked<unsigned>("firstLumiSection",1)->setComment("First lumi section to use");
  desc.addUntracked<int>("maxEventsPerLumiSection",-1)->setComment("Use this metric to instantiate a new lumi section");
  desc.addUntracked<bool>("useL1EventID", true)->setComment("Use L1 event ID from FED header if true or from TCDS FED if false");
  desc.addUntracked<std::vector<unsigned> >("fedIds",{0})->setComment("list of fedIds");
  desc.addUntracked<std::vector<std::string> >("inputs")->setComment("list of input files to use for DAQ");
  desc.addUntracked<std::vector<std::string> >("trig_inputs")->setComment("list of input files to use for TRIG");
  desc.setAllowAnything();
  descriptions.add("source", desc);
}

//
edm::RawInputSource::Next HGCalSlinkFromRawSource::checkNext() {

  bool status = updateRunAndEventInfo();

  //no valid event stop here
  if(!status || remainingEvents()==0) {
    std::cout << "End of file or events required reached" << std::endl;
    resetLuminosityBlockAuxiliary();
    return Next::kStop;
  }

  //increment event counter and check if lumi-section should be changed
  nEventsRead_++;
  if(maxEventsPerLumiSection_>0 && nEventsRead_>1 && nEventsRead_%maxEventsPerLumiSection_==0)
    lumiSectionVal_+=1;

  //start new lumi block
  if( !luminosityBlockAuxiliary() || luminosityBlockAuxiliary()->luminosityBlock() != lumiSectionVal_) {
    timeval tv;
    gettimeofday(&tv, nullptr);
    const edm::Timestamp lsopentime((unsigned long long)tv.tv_sec * 1000000 + (unsigned long long)tv.tv_usec);
    edm::LuminosityBlockAuxiliary* lumiBlockAuxiliary = \
      new edm::LuminosityBlockAuxiliary(runAuxiliary()->run(), lumiSectionVal_, lsopentime, edm::Timestamp::invalidTimestamp());
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
    throw cms::Exception("HGCalSlinkFromRawSource::read") <<  "set L1EventId from TCDS block is not implemented";

  //build the event auxiliary quantities
  eventID_ = edm::EventID(runNumberVal_, lumiSectionVal_, eventIdVal_);

  edm::TimeValue_t time;
  timeval stv;
  gettimeofday(&stv, nullptr);
  time = stv.tv_sec;
  time = (time << 32) + stv.tv_usec;
  edm::Timestamp tstamp(time);

  edm::EventAuxiliary aux(eventID_, processGUID(), tstamp, isRealData_, edm::EventAuxiliary::PhysicsTrigger);
  aux.setProcessHistoryID(processHistoryID_);
  makeEvent(eventPrincipal, aux);
    
  std::unique_ptr<edm::WrapperBase> edp(new edm::Wrapper<FEDRawDataCollection>(std::move(rawData_)));
  eventPrincipal.put(daqProvenanceHelper_.branchDescription(), std::move(edp), daqProvenanceHelper_.dummyProvenance());

  std::unique_ptr<edm::WrapperBase> emd(new edm::Wrapper<HGCalTestSystemMetaData>(std::move(metaData_)));
  eventPrincipal.put(metadataProvenanceHelper_.branchDescription(), std::move(emd), metadataProvenanceHelper_.dummyProvenance());
}

//
bool HGCalSlinkFromRawSource::updateRunAndEventInfo() {

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
      copyToFEDRawData(*rawData_, rEvent, fedId);
    } else {
      // find the event matched to the first slink
      while (rEvent) {
        if (rEvent->slinkBoe()->eventId() == eventIdVal_ && rEvent->slinkEoe()->bxId() == bxIdVal_ &&
            rEvent->slinkEoe()->orbitId() == orbitIdVal_) {
          copyToFEDRawData(*rawData_, rEvent, fedId);
          break;
        } else {
          edm::LogError("HGCalSlinkFromRawSource")
              << "Mismatch in E/B/O counters for fedId=" << fedId << ": expect eventId=" << eventIdVal_
              << ", bxId=" << bxIdVal_ << ", orbitId=" << orbitIdVal_ << ", got eventId = " << rEvent->slinkBoe()->eventId()
              << ", bxId = " << rEvent->slinkEoe()->bxId() << ", orbitId=" << rEvent->slinkEoe()->orbitId();
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

    while (rTrgEvent) {
      // find the trigger event matched to the first DAQ slink
      if (rTrgEvent->slinkBoe()->eventId() == eventIdVal_ && rTrgEvent->slinkEoe()->bxId() == bxIdVal_ &&
          rTrgEvent->slinkEoe()->orbitId() == orbitIdVal_) {
        reader->readTriggerData(*metaData_, rTrgEvent);
        break;
      } else {
        edm::LogError("SlinkFromRaw") << "Mismatch in E/B/O counters for the trigger link"
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

  return true;
}

DEFINE_FWK_INPUT_SOURCE(HGCalSlinkFromRawSource);
