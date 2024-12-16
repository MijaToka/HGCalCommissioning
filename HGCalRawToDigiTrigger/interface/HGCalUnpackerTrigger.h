/****************************************************************************
 *
 * A top level class dispatching unpacking of HGCal raw trigger data 
 * to specialized classes.
 * 
 * Authors: Jeremi Niedziela, Lovisa Rygaard
 *   
 *
 ****************************************************************************/

#ifndef HGCalCommissioning_HGCalRawToDigiTrigger_HGCalUnpackerTrigger_h
#define HGCalCommissioning_HGCalRawToDigiTrigger_HGCalUnpackerTrigger_h

#include "DataFormats/FEDRawData/interface/FEDRawData.h"
#include "CondFormats/HGCalObjects/interface/HGCalConfiguration.h"
#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalUnpackerTriggerSpecialization.h"

class HGCalUnpackerTrigger {
public:
  HGCalUnpackerTrigger() {}

  // TODO @hqucms
  // define what is needed as `config`
  // HGCalUnpackerTrigger(HGCalUnpackerTriggerConfig config);

  // TODO: should unpackingConfiguration be included in the config?

  void parseFEDData(const FEDRawData& fedData,
                    const HGCalModuleIndexerTrigger& moduleIndexer,
                    const HGCalConfiguration& config,
                    hgcaldigi::HGCalDigiTriggerHost& digisTrigger,
                    std::string unpackingConfiguration);

private:
  std::unique_ptr<HGCalUnpackerTriggerSpecialization> unpackerSpecialization_;
};

#endif
