#ifndef hgcal_slinkfromraw_Record_h
#define hgcal_slinkfromraw_Record_h

#include <iostream>
#include <cstring>

#include "RecordHeader.h"

namespace hgcal_slinkfromraw {
  class Record : public RecordHeader {
  public:
    Record() {
      reset();
    }
    
    inline const uint64_t* payload() const {
      return (uint64_t*)(this+1);
    }
    
    inline uint64_t* getPayload() {
      return (uint64_t*)(this+1);
    }

    inline void incrementPayloadLength(uint16_t l=1) {
      RecordHeader::setPayloadLength(payloadLength()+l);
    }
    
    inline void deepCopy(const Record &r) {
      std::memcpy(this,&r,8*r.totalLength());
    }

    inline void deepCopy(const Record *r) {
      deepCopy(*r);
    }

  };
  
  template<unsigned NumberOfPayloadWords> class RecordT : public Record {
  
  public:
    RecordT() {
      for(unsigned i(0);i<NumberOfPayloadWords;i++) {
	_payload[i]=0xdeadbeefdeadbeef;
      }
    }

    inline unsigned maxNumberOfPayloadWords() const {
      return NumberOfPayloadWords;
    }
    
    inline void setPayloadLength() {
      RecordHeader::setPayloadLength(NumberOfPayloadWords);
    }

    inline void setPayloadLength(uint16_t l) {
      RecordHeader::setPayloadLength(l);
    }
    
    inline const uint64_t* constPayload() {
      return _payload;
    }

    inline uint64_t* payload() {
      return _payload;
    }

    inline void print(std::ostream &o=std::cout) const {
      o << "Record::print()" << std::endl;
      RecordHeader::print(o," ");
      
      for(unsigned i(0);i<payloadLength();i++) {
	o << "   Payload word " << std::setw(5) << " = 0x"
	  << std::hex << std::setfill('0')
	  << std::setw(16) << _payload[i]
	  << std::dec << std::setfill(' ') << std::endl;
      }
    }
    
  protected:
    uint64_t _payload[NumberOfPayloadWords];
  private:
  };

}

#endif
