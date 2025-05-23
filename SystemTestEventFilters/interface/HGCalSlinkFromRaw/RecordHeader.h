#ifndef hgcal_slinkfromraw_RecordHeader_h
#define hgcal_slinkfromraw_RecordHeader_h

#include <iostream>
#include <iomanip>
#include <cstdint>


#include "FsmState.h"

namespace hgcal_slinkfromraw {

  class RecordHeader {
  
  public:
    enum Identifier {
      Pattern=0x33,
      
      StateData=0x33,
      ConfigurationData=0xcc,
      EventData=0xdd,
      EndOfIdentifierEnum,
    
      // For information
      FileContinuationEof=0xee,
      FileContinuationBof=0xbb,
    };

    RecordHeader() {
      reset();
    }

    inline void reset(FsmState::State s=FsmState::EndOfStateEnum) {
      _header=uint64_t(Pattern)<<56;
      setState(s);
    }
    
    // Get values
    inline uint8_t pattern() const {
      return _header>>56;
    }

    inline bool validPattern() const {
      return pattern()==Pattern;
    }
    
    inline Identifier identifier() const {
      return (Identifier)(_header>>56);
    }
    
    inline FsmState::State state() const {
      return (FsmState::State)((_header>>48)&0x7f);
    }
  
    inline bool validState() const {
      return state()<FsmState::EndOfStateEnum;
    }
    
    inline uint16_t payloadLength() const {
      return (_header>>32)&0x0fff; // LIMIT TO 4k FOR NOW
    }

    inline uint32_t totalLength() const {
      return payloadLength()+1;
    }

    inline uint32_t totalLengthInBytes() const {
      return sizeof(uint64_t)*(payloadLength()+1);
    }

    inline uint32_t utc() const {
      return _header&0xffffffff;
    }

    inline std::string utcDate() const {
      uint64_t t(utc());
      return ctime((time_t*)(&t));
    }
    
    inline uint32_t sequenceCounter() const {
      return _header&0xffffffff;
    }
    
    inline static const std::string identifierName(Identifier i) {
      if(i==StateData        ) return "StateData        ";
      if(i==ConfigurationData) return "ConfigurationData";
      if(i==EventData        ) return "EventData        ";
      return FsmState::_unknown;
    }

    inline const std::string identifierName() const {
      return identifierName(identifier());
    }

    // Set values
    inline void setIdentifier(Identifier i) {
      _header&=0x00ffffffffffffff;
      _header|=(uint64_t(i)<<56);
    }

    inline void setState(FsmState::State s) {
      _header&=0xff00ffffffffffff;
      _header|=(uint64_t(s)<<48);
      setIdentifier(StateData);
    }

    inline void setPayloadLength(uint16_t l) {
      _header&=0xffff0000ffffffff;
      _header|=(uint64_t(l)<<32);

    }

    inline void setUtc(uint32_t t=time(0)) {
      _header&=0xffffffff00000000;
      _header|=t;
    }

    inline void setSequenceCounter(uint32_t c) {
      _header&=0xffffffff00000000;
      _header|=c;
    }

    inline bool operator==(const RecordHeader &h) const {
      return _header==h._header;
    }
  
    inline void print(std::ostream &o=std::cout, std::string s="") const {
      o << s << "RecordHeader::print()  Data = 0x"
	<< std::hex << std::setfill('0')
	<< std::setw(16) << _header
	<< std::dec << std::setfill(' ') << std::endl;
      o << s << " Pattern = 0x"
	<< std::hex << std::setfill('0')
	<< std::setw(2) << unsigned(pattern())
	<< std::dec << std::setfill(' ')
	<< (validPattern()?" = valid":" = invalid")
	<< std::endl;
      //o << s << " Identifier = " << identifierName() << std::endl;
      o << s << " State   = " << FsmState::stateName(state())
	<< (validState()?" = valid":" = invalid")
	<< std::endl;
      
      if(FsmState::transientState(state())) {
	o << s << " UTC = " << std::setw(10) << utc() << " = " << utcDate(); // endl already in ctime
      } else {
	o << s << " Sequencer counter = " << sequenceCounter() << std::endl;
      }

      o << s << " Payload length = " << std::setw(6)
	<< payloadLength() << " eight-byte words " << std::endl;
      o << s << " Record length   = " << std::setw(6)
	<< totalLengthInBytes() << " bytes " << std::endl;
    }
  
  private:
    uint64_t _header;
    
    inline static std::string _unknown{"Unknown"};

    /*
      static const std::string _identifierNames[EndOfIdentifierEnum];
      const std::string RecordHeader::_identifierNames[EndOfIdentifierEnum]={
      "StateData     ",
      "ConfigurationData",
      "EventData        "
      };
    */
  };
}

#endif
