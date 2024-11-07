#ifndef HGCalCommissioning_DQM_interface_HGCalECONDPacketAnalysis_h
#define HGCalCommissioning_DQM_interface_HGCalECONDPacketAnalysis_h

#include <string>

namespace hgcal {

  /**
     @short this function re-computes the CRC of the ECON-D packet and compares it with the trailer of the packet
     false is returned if there is a mismatch
   */
  bool econdCRCAnalysis(const uint64_t *header, uint32_t pos, uint32_t payloadLength, uint64_t crcpol=0x4c11db7);


} // namespace hgcal

#endif
