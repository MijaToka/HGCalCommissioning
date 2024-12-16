/****************************************************************************
 *
 * Unpacker to decode HGCal raw trigger data from SLinks in the September 2024 
 * test beam configuration. Adapted from: 
 * gitlab.cern.ch/tsculac/hgcal10glinkreceiver/-/blob/test_beam_Sept_2024/econt_processor.cpp
 * 
 * Authors: Jeremi Niedziela, Lovisa Rygaard, Marco Chiusi
 * 
 ****************************************************************************/

#ifndef HGCalCommissioning_HGCalRawToDigiTrigger_HGCalUnpackerTriggerSpecialization_TBsep24_h
#define HGCalCommissioning_HGCalRawToDigiTrigger_HGCalUnpackerTriggerSpecialization_TBsep24_h

#include "DataFormats/HGCalDigi/interface/HGCalRawDataDefinitions.h"
#include "DataFormats/FEDRawData/interface/FEDRawData.h"
#include "CondFormats/HGCalObjects/interface/HGCalConfiguration.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "HGCalCommissioning/HGCalDigiTrigger/interface/HGCalDigiTriggerHost.h"
#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalUnpackerTriggerSpecialization.h"
#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalModuleIndexerTrigger.h"

class HGCalUnpackerTriggerSpecialization_TBsep24 : public HGCalUnpackerTriggerSpecialization {
public:
  HGCalUnpackerTriggerSpecialization_TBsep24(std::vector<uint64_t> words) : HGCalUnpackerTriggerSpecialization(words) {}

  void FillDigis(const HGCalModuleIndexerTrigger& moduleIndexer,
                 hgcaldigi::HGCalDigiTriggerHost& digisTrigger);

private:
  void run_unpacker(std::vector<uint8_t>& algo_type,
                    std::vector<bool>& valid,
                    std::vector<uint8_t>& BX_location,
                    std::vector<unsigned>& BX_energy,
                    unsigned train_number,
                    unsigned n_BXs,
                    unsigned aligned,
                    unsigned wanted_BX,
                    std::vector<uint8_t>& moduleIdx);

  static uint32_t unpack5E4MToUnsigned(uint32_t flt);
  int find_cafe_word(int n_packet, int cafe_word_loc = -1);
  std::tuple<int, int> get_scintillator_trigger_loc(int packet_location);

  void initialize_packet_with_words(std::map<int, std::vector<uint64_t>>& packet_per_BX, int i_BX, int& BX_id_h);
  uint64_t pick_bits64(uint64_t number, int start_bit, int number_of_bits);

  int get_channel_id(int n_header, int cafe_word_loc = -1);
  int get_buffer_status(int n_header, int cafe_word_loc = -1);
  int get_packet_size(int n_header, int cafe_word_loc = -1);
  int get_word_in_BX(int n_header, int cafe_word_loc = -1);
  int get_number_of_BXs(int n_header, int cafe_word_loc = -1);

  bool fill_algo_type_valid_and_moduleidx(std::string algo,
                                          unsigned wanted_BX,
                                          std::vector<uint8_t>& algo_type,
                                          std::vector<bool>& valid,
                                          std::vector<uint8_t>& moduleIdx);

  void set_packet_config(std::map<int, std::map<int, std::vector<uint64_t>>> packet,
                         std::map<std::string, std::vector<uint16_t>>& packet_locations,
                         uint16_t& module_sum,
                         std::map<std::string, std::vector<uint16_t>>& packet_energies,
                         std::map<std::string, std::vector<uint16_t>>& packet_locations_unpacked,
                         std::map<std::string, std::vector<uint32_t>>& packet_energies_unpacked,
                         std::vector<std::string> econt_config,
                         int BX_id_h,
                         int n_BXs,
                         int channel_id,
                         bool aligned,
                         int wanted_BX);

  void set_packet_energies(std::vector<uint16_t>& packet_energies, uint64_t word_energies, int n_TCs, int n_bits_TC);

  void set_packet_locations(
      std::vector<uint16_t>& packet_locations, uint64_t word_locations, int header, int n_TCs, int n_bits_TC);

  void get_unpacked_energies_locations(std::vector<uint16_t>& locations,
                                       std::vector<uint32_t>& energies,
                                       std::vector<uint64_t> packet,
                                       std::string algo,
                                       int n_module);
};

#endif
