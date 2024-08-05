#include "../interface/HGCalSlinkFileReader.h"

#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/Utilities/interface/Exception.h"

#include <ostream>
#include <iostream>
#include <fstream>

using namespace hgcal;

SlinkFileReader::SlinkFileReader(const std::vector<std::string> &filelist, unsigned fedId)
    : inputfiles_(filelist), fedId_(fedId), record_(new hgcal_slinkfromraw::RecordT<4095>) {
  std::cout << "[SlinkFileReader] fedId=" << fedId_ << ", files:\n";
  std::copy(std::begin(inputfiles_), std::end(inputfiles_), std::ostream_iterator<std::string>{std::cout, "\n"});
}

const hgcal_slinkfromraw::RecordRunning *SlinkFileReader::nextEvent() {
  if (inputfiles_.empty())
    return nullptr;

  // open a new file
  if (fileReader_.closed()) {
    fileReader_.open(inputfiles_[ifile_]);
  }

  //no more records in the file, move to next
  if (!fileReader_.read(record_)) {
    fileReader_.close();

    ifile_++;
    if (ifile_ >= inputfiles_.size()) {
      return nullptr;
    }
    return nextEvent();
  }

  //if record is stop or starting read again
  if (record_->state() == hgcal_slinkfromraw::FsmState::Stopping) {
    edm::LogInfo("SlinkFileReader") << "RecordStopping will search for next";
    const hgcal_slinkfromraw::RecordStopping *rStop((hgcal_slinkfromraw::RecordStopping *)record_);
    std::cout << "[fedId=" << fedId_ << "]\n";
    rStop->print();
    return nextEvent();
  }
  if (record_->state() == hgcal_slinkfromraw::FsmState::Starting) {
    edm::LogInfo("SlinkFileReader") << "RecordStarting will search for next";
    const hgcal_slinkfromraw::RecordStarting *rStart((hgcal_slinkfromraw::RecordStarting *)record_);
    std::cout << "[fedId=" << fedId_ << "]\n";
    rStart->print();
    return nextEvent();
  }
  if (record_->state() == hgcal_slinkfromraw::FsmState::Continuing) {
    edm::LogInfo("SlinkFileReader") << "RecordContinuing";
    const hgcal_slinkfromraw::RecordContinuing *rCont((hgcal_slinkfromraw::RecordContinuing *)record_);
    std::cout << "[fedId=" << fedId_ << "]\n";
    rCont->print();
    return nextEvent();
  }

  const auto *rEvent = (hgcal_slinkfromraw::RecordRunning *)record_;
  if (!rEvent->valid())
    throw cms::Exception("[SlinkFileReader::nextEvent]") << "record running is invalid for fedId=" << fedId_;

  if (firstEvent_) {
    std::cout << "[fedId=" << fedId_ << "]\n";
    rEvent->print();
    firstEvent_ = false;
  }

  return rEvent;
}

void SlinkFileReader::readTriggerData(HGCalTestSystemMetaData &metaData,
                                      const hgcal_slinkfromraw::RecordRunning *rTrgEvent,
                                      unsigned num_blocks,
                                      unsigned scintillator_block_id) {
  constexpr uint64_t pkt_mask = 0xff;
  constexpr uint64_t pkt_sep = 0xcafecafe;

  // TODO: use implementations from std <bit> in c++20
  constexpr auto countl_zero = [](uint32_t input) -> unsigned char {
    if (input == 0) {
      return 32;
    }
    constexpr uint32_t highestBit = 1 << 31;
    unsigned char result = 0;
    for (; (input & highestBit) == 0; input <<= 1) {
      ++result;
    }
    return result;
  };

  constexpr auto countr_zero = [](uint32_t input) -> unsigned char {
    if (input == 0) {
      return 32;
    }
    unsigned char result = 0;
    for (; (input & 1) == 0; input >>= 1) {
      ++result;
    }
    return result;
  };

  if (rTrgEvent && rTrgEvent->payloadLength() > 0) {
    metaData.trigType_ = rTrgEvent->slinkBoe()->l1aType();
    metaData.trigSubType_ = rTrgEvent->slinkBoe()->l1aSubType();
    metaData.trigTime_ = 0;
    metaData.trigWidth_ = 0;

    auto p = (const uint64_t *)rTrgEvent;
    uint32_t length = 0;
    p += 3;  // (1 record header + 2 slink header)
    for (unsigned iblock = 0; iblock < num_blocks && p < (const uint64_t *)rTrgEvent + rTrgEvent->payloadLength();
         ++iblock) {
      LogDebug("SlinkFileReader") << "Header: " << std::hex << std::setfill('0') << "0x" << *p << std::endl;
      if ((*p >> 32) != pkt_sep) {
        throw cms::Exception("CorruptData")
            << "Expected packet separator: 0x" << std::hex << pkt_sep << " read: 0x" << (*p >> 32) << " Event id: 0x"
            << rTrgEvent->slinkBoe()->eventId() << " Bx id: 0x" << rTrgEvent->slinkEoe()->bxId() << " Orbit id: 0x"
            << rTrgEvent->slinkEoe()->orbitId() << " BOE header: 0x" << rTrgEvent->slinkBoe()->boeHeader();
      }
      length = *p & pkt_mask;
      if (iblock < scintillator_block_id) {
        //copy from *(p+1) to *(p+length) (i.e. discard the fecafecafe... word) ?
        //std::cout << std::dec << iblock << std::endl;
        //for(uint32_t k=1; k<length+1; k++)
        //  std::cout << "\t 0x" << std::hex << *(p+k) << std::endl;
      } else if (iblock == scintillator_block_id) {
        // scintillator
        // the length should be 7 (BX) * 7 (64b) words
        // only the LS 32 bits are used
        // the first word per BX is a header pattern 0xaaaaaaaa, and the 2nd word is a 32-bit counter
        // only the last (7th) 64b word is used for trig data
        auto p_scint = p + 7;
        uint32_t trigtime = 0;
        uint32_t trigwidth = 0;
        bool triggered = false;
        while (p_scint <= p + length) {
          // Bits [31:  0] : External Trigger
          // Bits [63: 32] : 0x0
          // assert((*p_scint >> 32) == 0x0);
          // if ((*p_scint >> 32) != 0x0) {
          //   // FIXME
          //   LogDebug("SlinkFileReader") << "Cannot find pattern (0x0) in the scintillator word: 0x" << std::hex
          //                               << std::setfill('0') << *p_scint;
          // }
          uint32_t trigbits = *p_scint & 0xFFFFFFFF;
          LogDebug("SlinkFileReader") << "BX " << (p_scint - p) / 7 << ": " << std::hex << std::setfill('0') << "0x"
                                      << *p_scint << ", trigbits = "
                                      << "0x" << trigbits << std::endl;
          if (not triggered) {
            trigtime += countl_zero(trigbits);
            if (trigbits > 0) {
              // first BX with the trigger fired
              triggered = true;
              // count the 1s from the right
              trigwidth += countr_zero(~trigbits);
            }
          } else {
            // trigger already fired in previous BX
            if (trigbits > 0) {
              // trigger signal extends more than 1 BX
              // count the 1s from the left
              trigwidth += countl_zero(~trigbits);
            } else if (trigbits == 0) {
              // stop processing when the trigger is no longer fired
              break;
            }
          }
          p_scint += 7;
        }
        LogDebug("SlinkFileReader") << "==> trigtime = " << std::dec << std::setfill(' ') << trigtime
                                    << ", trigwidth = " << trigwidth << std::endl;
        metaData.trigTime_ = trigtime;
        metaData.trigWidth_ = trigwidth;
        break;
      }
      p += length + 1;
    }
  }
}
