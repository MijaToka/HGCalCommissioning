#include "HGCalCommissioning/HGCalRawToDigiTrigger/interface/HGCalUnpackerTriggerSpecialization_TBsep24.h"

using namespace hgcal;

void HGCalUnpackerTriggerSpecialization_TBsep24::FillDigis(const HGCalModuleIndexerTrigger& moduleIndexer,
                                                           hgcaldigi::HGCalDigiTriggerHost& digisTrigger) {
  // matrix definition
  std::vector<uint8_t> algo;       // 0==BC, 1==STC4, 2==STC16
  std::vector<uint8_t> moduleIdx;  // module number based on algo
  std::vector<bool> valid;
  std::vector<uint8_t> BX0_loc, BX1_loc, BX2_loc, BX3_loc, BX4_loc, BX5_loc, BX6_loc;
  std::vector<unsigned> BX0_energy, BX1_energy, BX2_energy, BX3_energy, BX4_energy, BX5_energy, BX6_energy;

  // Create arrays of references to hold the loc and energy vectors. Better way to do it?
  std::vector<uint8_t>* BX_loc[] = {&BX0_loc, &BX1_loc, &BX2_loc, &BX3_loc, &BX4_loc, &BX5_loc, &BX6_loc};
  std::vector<unsigned>* BX_energy[] = {
      &BX0_energy, &BX1_energy, &BX2_energy, &BX3_energy, &BX4_energy, &BX5_energy, &BX6_energy};

  int n_BXs = 7;
  for (int train = 0; train < 1; train++) {
    for (int i_BX = 0; i_BX < n_BXs; i_BX++) {
      run_unpacker(algo, valid, *BX_loc[i_BX], *BX_energy[i_BX], train, n_BXs, 0, i_BX, moduleIdx);

      LogDebug("[HGCalUnpackerTrigger]") << "BX: " << i_BX << std::endl;
      LogDebug("[HGCalUnpackerTrigger]") << BX_loc[i_BX]->size() << valid.size() << algo.size()
                                         << BX_energy[i_BX]->size() << std::endl;

      for (unsigned i = 0; i < BX_loc[i_BX]->size(); i++) {
        LogDebug("[HGCalUnpackerTrigger]") << "loc: " << static_cast<unsigned int>((*BX_loc[i_BX])[i])
                                           << " valid: " << valid[i] << " algo: " << static_cast<unsigned int>(algo[i])
                                           << " energy: " << static_cast<unsigned int>((*BX_energy[i_BX])[i])
                                           << " module idx: " << static_cast<unsigned int>(moduleIdx[i]) << std::endl;
      }

      assert(BX_loc[i_BX]->size() == BX_energy[i_BX]->size() && valid.size() == BX_energy[i_BX]->size() &&
             algo.size() == BX_energy[i_BX]->size());
    }

    // loop over channels - assuming all bunch crossings should have same number of channels as BX0
    // TODO - fix these loops
    for (unsigned i = 0; i < BX_loc[0]->size(); i++) {
      auto algo_ = algo[i];
      auto valid_ = valid[i];
      auto moduleIdx_ = moduleIdx[i];
      auto channel_ = (*BX_loc[0])[i];
      uint32_t index = moduleIndexer.getIndexForModuleData(train, moduleIdx_, channel_);
      digisTrigger.view()[index].valid() = valid_;
      digisTrigger.view()[index].algo() = algo_;
      // assuming that the BX order follo 0=-3, 1=-2, 2=-1, 3=0, 4=1, 5=2, 6=3
      digisTrigger.view()[index].BXm3_location() = (*BX_loc[0])[i];
      digisTrigger.view()[index].BXm2_location() = (*BX_loc[1])[i];
      digisTrigger.view()[index].BXm1_location() = (*BX_loc[2])[i];
      digisTrigger.view()[index].BX0_location() = (*BX_loc[3])[i];
      digisTrigger.view()[index].BXp1_location() = (*BX_loc[4])[i];
      digisTrigger.view()[index].BXp2_location() = (*BX_loc[5])[i];
      digisTrigger.view()[index].BXp3_location() = (*BX_loc[6])[i];
      digisTrigger.view()[index].BXm3_energy() = (*BX_energy[0])[i];
      digisTrigger.view()[index].BXm2_energy() = (*BX_energy[1])[i];
      digisTrigger.view()[index].BXm1_energy() = (*BX_energy[2])[i];
      digisTrigger.view()[index].BX0_energy() = (*BX_energy[3])[i];
      digisTrigger.view()[index].BXp1_energy() = (*BX_energy[4])[i];
      digisTrigger.view()[index].BXp2_energy() = (*BX_energy[5])[i];
      digisTrigger.view()[index].BXp3_energy() = (*BX_energy[6])[i];
      digisTrigger.view()[index].flags() = hgcal::DIGI_FLAG::Normal;
      digisTrigger.view()[index].layer() = train;
      digisTrigger.view()[index].moduleIdx() = moduleIdx_;
    }
  }
}

void HGCalUnpackerTriggerSpecialization_TBsep24::run_unpacker(std::vector<uint8_t>& algo_type,
                                                              std::vector<bool>& valid,
                                                              std::vector<uint8_t>& BX_location,
                                                              std::vector<unsigned>& BX_energy,
                                                              unsigned train_number,
                                                              unsigned n_BXs,
                                                              unsigned aligned,
                                                              unsigned wanted_BX,
                                                              std::vector<uint8_t>& moduleIdx) {
  auto [trigger_loc, trigger_width] =
      get_scintillator_trigger_loc(6);  // Scintillator data is in the 6th packet of payload

  LogDebug("[HGCalUnpackerTriggerSpecialization_TBsep24]")
      << "trigger_loc " << trigger_loc << " trigger_width " << trigger_width << std::endl;

  // ECON-Ts configuration: BC, STC4, STC16
  std::vector<std::string> econt_config;
  if (train_number == 0) {
    econt_config = {"BC2", "BC1", "BC0"};
  } else {
    econt_config = {"STC42", "STC41", "STC40"};
  }

  std::map<int, std::map<int, std::vector<uint64_t>>> packet;  // keys: BX_index, channel_id

  std::map<std::string, std::vector<uint16_t>> packet_locations;
  std::map<std::string, std::vector<uint16_t>> packet_energies;

  std::map<std::string, std::vector<uint16_t>> packet_locations_unpacked;
  std::map<std::string, std::vector<uint32_t>> packet_energies_unpacked;

  uint16_t module_sum;  // unused
  int BX_id_h = 0;      // unused

  for (unsigned int i_BX = 0; i_BX < n_BXs; ++i_BX) {
    initialize_packet_with_words(packet[i_BX], i_BX, BX_id_h);
  }

  set_packet_config(packet,
                    packet_locations,
                    module_sum,
                    packet_energies,
                    packet_locations_unpacked,
                    packet_energies_unpacked,
                    econt_config,
                    BX_id_h,
                    n_BXs,
                    train_number + 1,
                    aligned,
                    wanted_BX);

  int nTCs = 0;

  std::map<std::string, int> algo_to_nTCs = {
      {"BC0", 4}, {"BC1", 4}, {"BC2", 4}, {"STC16", 3}, {"STC42", 10}, {"default", 6}};

  for (std::string algo : econt_config) {
    nTCs = algo_to_nTCs.find(algo) != algo_to_nTCs.end() ? algo_to_nTCs[algo] : algo_to_nTCs["default"];

    for (int i = 0; i < nTCs; i++) {
      if (fill_algo_type_valid_and_moduleidx(algo, wanted_BX, algo_type, valid, moduleIdx)) {
        BX_energy.push_back(unpack5E4MToUnsigned(packet_energies_unpacked[algo][i]));
        BX_location.push_back(packet_locations_unpacked[algo][i]);
      } else {
        BX_energy.push_back(unpack5E4MToUnsigned(0));
        BX_location.push_back(0);
      }
    }
  }
}

uint32_t HGCalUnpackerTriggerSpecialization_TBsep24::unpack5E4MToUnsigned(uint32_t flt) {
  assert(flt < 0x200);

  uint32_t e((flt >> 4) & 0x1f);
  uint32_t m((flt) & 0x0f);

  if (e == 0) {
    return m;
  } else if (e == 1) {
    return 16 + m;
  } else {
    return (32 + 2 * m + 1) << (e - 2);
  }
}

// returns location in this event of the n'th 0xfecafe... line
int HGCalUnpackerTriggerSpecialization_TBsep24::find_cafe_word(int n_packet, int cafe_word_loc) {
  int cafe_counter = 0;
  for (unsigned iword = 0; iword < words_.size(); ++iword) {
    uint64_t word = words_[iword];

    if ((word >> 32) == 0xcafecafe) {
      cafe_counter++;
      if (cafe_counter == n_packet) {
        cafe_word_loc = iword;
      }
    }
  }
  return cafe_word_loc;
}

void HGCalUnpackerTriggerSpecialization_TBsep24::initialize_packet_with_words(
    std::map<int, std::vector<uint64_t>>& packet_per_BX, int i_BX, int& BX_id_h) {
  int word_idx = 0;

  for (int n_header = 1; n_header <= 11; n_header++) {
    int start_word_idx = find_cafe_word(n_header);
    if (start_word_idx == -1) {
      if (i_BX == 0) {
        BX_id_h = words_[word_idx + 2] & 0x7;
      }
      continue;
    }
    int channel_id = get_channel_id(n_header);
    // int buffer_status = get_buffer_status(n_header);  // unused
    // int packet_size = get_packet_size(n_header);  // unused
    int n_words_in_BX = get_word_in_BX(n_header);
    // int n_BX = get_number_of_BXs(n_header);  // unused

    if (channel_id != n_header - 1) {
      std::cout << "Channel from header " << channel_id << ", expected " << n_header << std::endl;
    }
    /*
    std::cout << "loc header " << start_word_idx << " size " << packet_size << " ch_id " << channel_id << " bufstat " \
      << buffer_status << " nofwd_perbx " << n_words_in_BX << " nofBX " << n_BX << std::endl;
      */
    for (int j = 0; j < n_words_in_BX; j++) {
      word_idx = start_word_idx + 1 + n_words_in_BX * i_BX + j;
      packet_per_BX[channel_id].push_back(words_[word_idx]);
    }
  }
}

// get the total number of BX stored in an event
int HGCalUnpackerTriggerSpecialization_TBsep24::get_number_of_BXs(int n_header, int cafe_word_loc) {
  int header_loc = find_cafe_word(n_header, cafe_word_loc);
  const uint64_t header = words_[header_loc];
  const uint64_t n_words_in_packet = pick_bits64(header, 56, 8);
  const uint64_t n_words_in_BX = pick_bits64(header, 40, 4);

  int n_BXs = -1;
  if (n_words_in_BX != 0) {
    n_BXs = n_words_in_packet / n_words_in_BX;
  } else {
    std::cout << "Number of words per BX not initialized!" << std::endl;
    std::abort();
  }
  return n_BXs;
}

// get the number of words in BX
int HGCalUnpackerTriggerSpecialization_TBsep24::get_word_in_BX(int n_header = 1, int cafe_word_loc) {
  int header_loc = find_cafe_word(n_header, cafe_word_loc);
  const uint64_t header = words_[header_loc];
  return pick_bits64(header, 40, 4);
}

// get packet size
int HGCalUnpackerTriggerSpecialization_TBsep24::get_packet_size(int n_header, int cafe_word_loc) {
  int header_loc = find_cafe_word(n_header, cafe_word_loc);
  const uint64_t header = words_[header_loc];
  return pick_bits64(header, 56, 8);
}

// get buffer status
int HGCalUnpackerTriggerSpecialization_TBsep24::get_buffer_status(int n_header, int cafe_word_loc) {
  int header_loc = find_cafe_word(n_header, cafe_word_loc);
  const uint64_t header = words_[header_loc];
  return pick_bits64(header, 44, 4);
}

// get channel_id
int HGCalUnpackerTriggerSpecialization_TBsep24::get_channel_id(int n_header, int cafe_word_loc) {
  int header_loc = find_cafe_word(n_header, cafe_word_loc);
  const uint64_t header = words_[header_loc];
  return pick_bits64(header, 48, 8);
}

uint64_t HGCalUnpackerTriggerSpecialization_TBsep24::pick_bits64(uint64_t number, int start_bit, int number_of_bits) {
  // Create a mask to extract the desired bits.
  uint64_t mask = (1 << number_of_bits) - 1;
  // Shift the number to the start bit position.
  number = number >> (64 - start_bit - number_of_bits);
  // Mask the number to extract the desired bits.
  uint64_t picked_bits = number & mask;

  return picked_bits;
}

// assigning TC or STCs energies
void HGCalUnpackerTriggerSpecialization_TBsep24::set_packet_energies(std::vector<uint16_t>& packet_energies,
                                                                     uint64_t word_energies,
                                                                     int n_TCs,
                                                                     int n_bits_TC) {
  for (int i = 0; i < n_TCs; i++) {
    packet_energies.push_back(pick_bits64(word_energies, i * n_bits_TC, n_bits_TC) & 0x7F);
  }
}

// assigning TC or STCs addresses
void HGCalUnpackerTriggerSpecialization_TBsep24::set_packet_locations(
    std::vector<uint16_t>& packet_locations, uint64_t word_locations, int header, int n_TCs, int n_bits_TC) {
  for (int i = 0; i < n_TCs; i++) {
    LogDebug("[HGCalUnpackerTriggerSpecialization_TBsep24]")
        << std::hex << "word_location " << word_locations << " local location "
        << pick_bits64(word_locations, header + i * n_bits_TC, n_bits_TC) << std::dec << std::endl;
    packet_locations.push_back(pick_bits64(word_locations, header + i * n_bits_TC, n_bits_TC) & 0x3F);
  }
}

void HGCalUnpackerTriggerSpecialization_TBsep24::get_unpacked_energies_locations(std::vector<uint16_t>& locations,
                                                                                 std::vector<uint32_t>& energies,
                                                                                 std::vector<uint64_t> packet,
                                                                                 std::string algo,
                                                                                 int n_module) {
  /* Older version we received from Marco during September test beam
  for (long unsigned int word_idx = 1; word_idx < packet.size() - 1; ++word_idx) {
    uint16_t econt_word = 0;
    if (algo.find("BC") != std::string::npos) {
      if (n_module != 2 and word_idx > 4)
        break;
      if (n_module == 2)
        econt_word = (packet[word_idx]) & 0xFFFF;
      else
        econt_word = (packet[word_idx] >> (16 * (2 - n_module) + 16)) & 0xFFFF;
    } else {
      std::cout << "NOT IMPLEMENTED !!!" << std::endl;
    }
    if (algo == "STC16" and word_idx > 3)
      break;  // STC16 uses only first 3 words, not all 6

    LogDebug("[HGCalUnpackerTriggerSpecialization_TBsep24]") << "module " << n_module << " word " << std::hex << word_idx << " location " << std::dec
              << (econt_word & 0x3F) << std::endl;
    locations.push_back(econt_word & 0x3F);
    energies.push_back((econt_word >> 6) & 0x1FF);
  }
*/

  // new version from gitlab.cern.ch/tsculac/hgcal10glinkreceiver/-/blob/test_beam_Sept_2024/econt_processor.cpp
  for (long unsigned int word_idx = 1; word_idx < packet.size(); ++word_idx) {
    uint16_t econt_word = 0, econt_word_1 = 0;
    if (algo.find("BC") != std::string::npos) {
      if (n_module != 2 and word_idx > 4)
        continue;
      if (word_idx > 6)
        break;
      if (n_module == 2)
        econt_word = (packet[word_idx]) & 0xFFFF;
      else
        econt_word = (packet[word_idx] >> (16 * (2 - n_module) + 16)) & 0xFFFF;
    } else if (algo.find("STC4") != std::string::npos) {
      if (word_idx > 6)
        break;
      if (n_module == 2 and word_idx > 5)
        continue;
      if (n_module == 2) {
        econt_word = (packet[word_idx]) & 0xFFFF;
        econt_word_1 = (packet[word_idx] >> 16) & 0xFFFF;
      } else
        econt_word = (packet[word_idx] >> (16 * (2 - n_module) + 16)) & 0xFFFF;
    } else if (algo.find("MB") != std::string::npos) {
      if (word_idx > 4)
        break;
      econt_word = (packet[word_idx]) & 0xFFFF;
      econt_word_1 = (packet[word_idx] >> 16) & 0xFFFF;
    }
    if (algo == "STC16" and word_idx > 3)
      break;  // STC16 uses only first 3 words, not all 6

    LogDebug("[HGCalUnpackerTriggerSpecialization_TBsep24]")
        << "UNPACKING module " << n_module << "word " << std::hex << econt_word << " energy "
        << ((econt_word >> 6) & 0x1FF) << " location " << std::dec << ((econt_word >> 2) & 0xF) << std::endl;

    if (algo.find("BC") != std::string::npos)
      locations.push_back(econt_word & 0x3F);
    else {
      locations.push_back(((econt_word >> 2) & 0xF));  // 4-bits loc + 2 bits TC max
      // locations_TC.push_back(econt_word & 0x3);
    }
    energies.push_back(((econt_word >> 6) & 0x1FF));

    if ((n_module == 2 and algo.find("STC4") != std::string::npos) or (algo.find("MB") != std::string::npos)) {
      // locations_TC.push_back(econt_word_1 & 0x3);
      locations.push_back(((econt_word_1 >> 2) & 0xF));
      energies.push_back(((econt_word_1 >> 6) & 0x1FF));
    }
  }
}

bool HGCalUnpackerTriggerSpecialization_TBsep24::fill_algo_type_valid_and_moduleidx(std::string algo,
                                                                                    unsigned wanted_BX,
                                                                                    std::vector<uint8_t>& algo_type,
                                                                                    std::vector<bool>& valid,
                                                                                    std::vector<uint8_t>& moduleIdx) {
  auto find_algo = [&algo](std::string x) { return algo.find(x) != std::string::npos; };

  if (find_algo("BC")) {
    if (wanted_BX == 0) {
      algo_type.push_back(0);
      valid.push_back(true);
    } else {
      assert(algo_type.back() == 0);
    }
    moduleIdx.push_back(std::stoi(algo.substr(2)));
  } else if (find_algo("STC4")) {
    if (wanted_BX == 0) {
      algo_type.push_back(1);
      valid.push_back(true);
    } else {
      assert(algo_type.back() == 1);
    }
    moduleIdx.push_back(std::stoi(algo.substr(4)));
  } else if (find_algo("STC16")) {
    if (wanted_BX == 0) {
      algo_type.push_back(2);
      valid.push_back(true);
    } else {
      assert(algo_type.back() == 2);
    }
    moduleIdx.push_back(0);
  } else {
    if (wanted_BX == 0) {
      valid.push_back(false);  // Invalid algo
    } else {
      algo_type.back() = 0;
      moduleIdx.back() = 0;
    }
    return false;
  }
  return true;
}

void HGCalUnpackerTriggerSpecialization_TBsep24::set_packet_config(
    std::map<int, std::map<int, std::vector<uint64_t>>> packet,
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
    int wanted_BX) {
  int word_idx = 0, n_module = 2;
  // if (aligned) wanted_BX = 3; // if no match with Slink header, choose the central BX

  for (std::string algo : econt_config) {
    if (algo.find("BC") != std::string::npos) {
      if (aligned) {
        wanted_BX = 0;
      }
      if (packet_locations[algo].size() == 0 or !aligned) {
        if ((algo.back() - '0') == 2) {
          uint64_t wordBC_locations = pick_bits64(packet[wanted_BX][channel_id][word_idx], 0, 48) << 16;
          uint64_t wordBC_energy = (pick_bits64(packet[wanted_BX][channel_id][word_idx], 48, 16) << 48) +
                                   ((packet[wanted_BX][channel_id][word_idx + 1] >> 32) << 16);
          module_sum = pick_bits64(wordBC_locations, 4, 8);
          set_packet_locations(packet_locations[algo], wordBC_locations, 4 + 8, 6, 6);
          set_packet_energies(packet_energies[algo], wordBC_energy, 6, 7);
        } else {
          uint64_t wordBC_locations = (pick_bits64(packet[wanted_BX][channel_id][word_idx], 32, 32) << 32) +
                                      ((packet[wanted_BX][channel_id][word_idx + 1] >> 60) << 28);
          LogDebug("[HGCalUnpackerTriggerSpecialization_TBsep24]")
              << std::hex << ((packet[wanted_BX][channel_id][word_idx + 1] >> 60) << 28) << std::dec << std::endl;
          uint64_t wordBC_energy = (packet[wanted_BX][channel_id][word_idx + 1] >> 32) << 36;
          module_sum = pick_bits64(wordBC_locations, 4, 8);
          set_packet_locations(packet_locations[algo], wordBC_locations, 4 + 8, 4, 6);
          set_packet_energies(packet_energies[algo], wordBC_energy, 4, 7);
        }
        get_unpacked_energies_locations(packet_locations_unpacked[algo],
                                        packet_energies_unpacked[algo],
                                        packet[wanted_BX][channel_id + 4],
                                        algo,
                                        algo.back() - '0');
      }
    }
    if (algo == "STC4") {
      if (aligned) {
        wanted_BX = 2;
      }
      if (packet_locations["STC4"].size() == 0 or !aligned) {
        // std::cout << "Selecting BX for STC4 " << wanted_BX << std::endl;
        uint64_t wordSTC4_locations = pick_bits64(packet[wanted_BX][channel_id][word_idx], 32, 16) << 48;
        uint64_t wordSTC4_energy = (pick_bits64(packet[wanted_BX][channel_id][word_idx], 48, 16) << 48) +
                                   ((packet[3][channel_id][word_idx + 1] >> 32) << 16);
        set_packet_locations(packet_locations["STC4"], wordSTC4_locations, 4, 6, 2);
        set_packet_energies(packet_energies["STC4"], wordSTC4_energy, 6, 7);
        get_unpacked_energies_locations(packet_locations_unpacked[algo],
                                        packet_energies_unpacked[algo],
                                        packet[wanted_BX][channel_id + 4],
                                        algo,
                                        n_module);
      }
    }
    if (algo == "STC16") {
      if (aligned) {
        wanted_BX = 2;
      }
      if (packet_locations["STC16"].size() == 0 or !aligned) {
        // std::cout << "Selecting BX for STC16 " << wanted_BX << std::endl;
        uint64_t wordSTC16_locations = pick_bits64(packet[wanted_BX][channel_id][word_idx], 32, 16) << 48;
        uint64_t wordSTC16_energy = (pick_bits64(packet[wanted_BX][channel_id][word_idx], 48, 16) << 48) +
                                    ((packet[3][channel_id][word_idx + 1] >> 32) << 16);
        set_packet_locations(packet_locations["STC16"], wordSTC16_locations, 4, 6, 2);
        set_packet_energies(packet_energies["STC16"], wordSTC16_energy, 6, 7);
        get_unpacked_energies_locations(packet_locations_unpacked[algo],
                                        packet_energies_unpacked[algo],
                                        packet[wanted_BX][channel_id + 4],
                                        algo,
                                        n_module);
      }
    }
    word_idx += 1;
    n_module -= 1;
  }
}

// scintillator triggers during BX, find the time within the whole BX window
// possible output is N_BX*[0,32]
std::tuple<int, int> HGCalUnpackerTriggerSpecialization_TBsep24::get_scintillator_trigger_loc(int packet_location) {
  int timing_word_start_idx =
      find_cafe_word(packet_location) +
      7;  // Scintilator data is a 7th word within the packet (right before 0x00000000aaaaaaaa separator)
  int trigger_loc = 0;
  int trigger_width = 0;
  bool trigger = 0;  // boolean that tells us if trigger happened
  for (unsigned i(timing_word_start_idx); i < words_.size();
       i = i + 7)  // There are total 7 words of scintillator data in each sub-packet
  {
    const uint32_t timing_word = words_[i];
    if (timing_word == 0 && !trigger) {
      trigger_loc = trigger_loc + 32;
    } else if (timing_word != 0 && !trigger) {
      // use built in function to find number of leading zeros
      trigger_loc = trigger_loc + __builtin_clz(timing_word);
      trigger = 1;
      trigger_width = 32 - __builtin_clz(timing_word);
    } else if (timing_word == 0xffffffff && trigger) {
      trigger_width = trigger_width + 32;
    } else if (timing_word != 0 && trigger) {
      trigger_width = trigger_width + (32 - __builtin_ctz(timing_word));
    }
  }
  return std::make_tuple(trigger_loc, trigger_width);
}
