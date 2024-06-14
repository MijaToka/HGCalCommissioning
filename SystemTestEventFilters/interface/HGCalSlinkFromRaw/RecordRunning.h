#ifndef hgcal_slinkfromraw_RecordRunning_h
#define hgcal_slinkfromraw_RecordRunning_h

#include <iostream>
#include <cstdint>
#include <algorithm>

#include "BePacketHeader.h"
#include "SlinkBoe.h"
#include "SlinkEoe.h"
#include "Record.h"

namespace hgcal_slinkfromraw {

  class RecordRunning : public Record {
  
  public:
    RecordRunning() {
    }

    // Ensure has a 128-bit word structure
    inline void setPayloadLength(uint16_t l) {
      if((l%2)==1) l++;
      RecordHeader::setPayloadLength(l);
    }
    
    inline void setHeader(uint32_t t=time(0)) {
      setIdentifier(RecordHeader::EventData);
      setState(FsmState::Running);
      setPayloadLength(0);
      setUtc(t);
    }

    inline bool valid() const {
      return validPattern() && state()==FsmState::Running;
    }
    
    inline const SlinkBoe* slinkBoe() const {
      return (SlinkBoe*)_payload;
    }
    
    inline const uint32_t* daqPayload() const {
      return (payloadLength()==0?nullptr:(const uint32_t*)(_payload+2));
    }
    
    inline const BePacketHeader* bePacketHeader() const {
      return (const BePacketHeader*)daqPayload();
    }

    inline const uint32_t* econdPayload() const {
      return (payloadLength()==0?nullptr:(const uint32_t*)(_payload+3));
    }
    
    inline const SlinkEoe* slinkEoe() const {
      return (SlinkEoe*)(_payload+payloadLength()-2);
    }
    
    inline SlinkBoe* getSlinkBoe() {
      return (SlinkBoe*)_payload;
    }
    
    inline uint32_t* getDaqPayload() {
      return (payloadLength()==0?nullptr:(uint32_t*)(_payload+2));
    }
    
    inline BePacketHeader* getBePacketHeader() {
      return (BePacketHeader*)daqPayload();
    }

    inline uint32_t* getEcondPayload() {
      return (payloadLength()==0?nullptr:(uint32_t*)(_payload+3));
    }
    
    inline SlinkEoe* getSlinkEoe() {
      return (SlinkEoe*)(_payload+payloadLength()-2);
    }
    
    inline void print(std::ostream &o=std::cout, std::string s="") const {
      o << s << "RecordRunning::print()" << std::endl;
      RecordHeader::print(o,s+" ");
           
      //for(unsigned i(0);i<payloadLength();i++) {
      //	o << s << "   Payload word " << std::setw(5) << " = 0x"
      //	  << std::hex << std::setfill('0')
      //	  << std::setw(16) << _payload[i]
      //	  << std::dec << std::setfill(' ') << std::endl;
      //}
      
      slinkBoe()->print(o,s+" ");
      if(bePacketHeader()!=nullptr) bePacketHeader()->print(o,s+" ");
      slinkEoe()->print(o,s+" ");
    }
    
  private:
    uint64_t _payload[4];
    
  };

}

#endif
