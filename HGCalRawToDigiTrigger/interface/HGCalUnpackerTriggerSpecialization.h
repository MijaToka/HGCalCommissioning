/****************************************************************************
 *
 * A base class for specialized unpacker classes to decode HGCal raw trigger 
 * data in different configurations (test beams, different runs, etc.)
 * 
 * Authors: Jeremi Niedziela
 *   
 ****************************************************************************/

#ifndef HGCalCommissioning_HGCalRawToDigiTrigger_HGCalUnpackerTriggerSpecialization_h
#define HGCalCommissioning_HGCalRawToDigiTrigger_HGCalUnpackerTriggerSpecialization_h

#include "HGCalCommissioning/HGCalDigiTrigger/interface/HGCalDigiTriggerHost.h"
#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalModuleIndexerTrigger.h"

class HGCalUnpackerTriggerSpecialization {
public:
  HGCalUnpackerTriggerSpecialization(std::vector<uint64_t> words) : words_(words) {}
  virtual ~HGCalUnpackerTriggerSpecialization() = default;

  virtual void FillDigis(const HGCalModuleIndexerTrigger& moduleIndexer,
                         hgcaldigi::HGCalDigiTriggerHost& digisTrigger) = 0;

protected:
  std::vector<uint64_t> words_;
};

#endif
