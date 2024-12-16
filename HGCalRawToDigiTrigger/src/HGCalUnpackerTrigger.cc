#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalUnpackerTrigger.h"

// Include your specialization of the unpacker here:
#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalUnpackerTriggerSpecialization_TBsep24.h"

using namespace hgcal;

void HGCalUnpackerTrigger::parseFEDData(const FEDRawData& fedData,
                                        const HGCalModuleIndexerTrigger& moduleIndexer,
                                        const HGCalConfiguration& config,
                                        hgcaldigi::HGCalDigiTriggerHost& digisTrigger,
                                        std::string unpackingConfiguration) {
  
  // Endianness assumption
  // From 32-bit word(ECOND) to 64-bit word(capture block): little endianness
  // Others: big endianness

  // TODO: if this also depends on the unpacking configuration, it should be moved to the specialization
  const auto* const header = reinterpret_cast<const uint64_t*>(fedData.data());
  const auto* const trailer = reinterpret_cast<const uint64_t*>(fedData.data() + fedData.size());
  LogDebug("[HGCalUnpackerTrigger]") << " nwords (64b) = " << std::distance(header, trailer) << "\n";

  std::vector<uint64_t> words;
  const auto* ptr = header;
  for (unsigned iword = 0; ptr < trailer; ++iword) {
    LogDebug("[HGCalUnpackerTrigger]") << std::setw(8) << iword << ": 0x" << std::hex << std::setfill('0')
                                       << std::setw(16) << *ptr << " (" << std::setfill('0') << std::setw(8)
                                       << *(reinterpret_cast<const uint32_t*>(ptr) + 1) << " " << std::setfill('0')
                                       << std::setw(8) << *reinterpret_cast<const uint32_t*>(ptr) << ")\n"
                                       << std::dec;
    uint64_t word = *ptr;
    words.push_back(word);
    ++ptr;
  }

  // Add your specialized class here, matching the string that will be passed on from the config file
  if(unpackingConfiguration == "TBsep24"){
    unpackerSpecialization_ = std::make_unique<HGCalUnpackerTriggerSpecialization_TBsep24>(words);
  }
  else{
    throw cms::Exception("HGCalUnpackerTrigger") << "Unknown unpacking configuration: " << unpackingConfiguration;
  }

  unpackerSpecialization_->FillDigis(moduleIndexer, digisTrigger);

}

