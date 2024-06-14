#ifndef hgcal_slinkfromraw_SlinkEoe_h
#define hgcal_slinkfromraw_SlinkEoe_h

#include <iostream>
#include <iomanip>
#include <cstdint>

namespace hgcal_slinkfromraw {


class SlinkEoe {
 public:
  enum {
    EoePattern=0xaa
  };
  
  SlinkEoe() {
    reset();
  }

  SlinkEoe(uint32_t l, uint16_t b, uint32_t o, uint16_t c, uint16_t s) {
    reset();

    setEventLength(l);
    setBxId(b);
    setOrbitId(o);
    setCrc(c);
    setStatus(s);
  }

  inline void reset() {
   _word[1]=uint64_t(EoePattern)<<56;
   _word[0]=0;
  }

  inline uint8_t  eoeHeader() const {
    return _word[1]>>56;
  }

  inline bool validPattern() const {
    return eoeHeader()==EoePattern;
  }

  inline uint16_t daqCrc() const {
    return (_word[1]>>40)&0xffff;
  }

  inline uint32_t eventLength() const {
    return (_word[1]>>12)&0xfffff;
  }

  inline uint16_t bxId() const {
    return _word[1]&0xfff;
  }

  inline uint32_t orbitId() const {
    return _word[0]>>32;
  }

  inline uint16_t crc() const {
    return (_word[0]>>16)&0xffff;
  }

  inline uint16_t status() const {
    return _word[0]&0xffff;
  }

  inline void setDaqCrc(uint16_t c) {  
    _word[1]&=0xff0000ffffffffff;
    _word[1]|=uint64_t(c)<<40;
  }

  inline void setEventLength(uint32_t l) {
    assert(l<(1U<<20));
    _word[1]&=0xffffffff00000fff;
    _word[1]|=(uint64_t(l)<<12);
  }

  inline void setBxId(uint16_t b) {
    assert(b>0 && b<=3564);
    _word[1]&=0xfffffffffffff000;
    _word[1]|=b;
  }

  inline void setOrbitId(uint32_t o) {
    _word[0]&=0x00000000ffffffff;
    _word[0]|=uint64_t(o)<<32;    
  }

  inline void setCrc(uint16_t c) {  
    _word[0]&=0xffffffff0000ffff;
    _word[0]|=uint64_t(c)<<16;    
  }

  inline void setStatus(uint16_t s) {  
    _word[0]&=0xffffffffffff0000;
    _word[0]|=s;
  }

  inline void incrementEventLength() {
    setEventLength(eventLength()+1);
  }
  
  inline bool valid() const {
    return eoeHeader()==EoePattern;
  }

  inline void print(std::ostream &o=std::cout, const std::string &s="") const {
    o << s << "SlinkEoe::print()  words = 0x"
      << std::hex << std::setfill('0')
      << std::setw(16) << _word[1] << ", 0x"
      << std::setw(16) << _word[0]
      << std::dec << std::setfill(' ')
      << std::endl;
    o << s << " EOE header = 0x"
      << std::hex << std::setfill('0')
      << std::setw(2) << unsigned(eoeHeader())
      << std::dec << std::setfill(' ')
      << std::endl;
    o << s << " DAQ CRC = 0x"
      << std::hex << std::setfill('0')
      << std::setw(4) << daqCrc()
      << std::dec << std::setfill(' ')
      << std::endl;
    o << s << " Event length in 128-bit words = "
      << std::setw(7) << eventLength()
      << std::endl;
    o << s << " BX id = " << std::setw(4) << bxId() << std::endl;
    o << s << " Orbit id = " << std::setw(10) << orbitId() << std::endl;
    o << s << " CRC = 0x"
      << std::hex << std::setfill('0')
      << std::setw(4) << crc()
      << std::dec << std::setfill(' ')
      << std::endl;
    o << s << " Status = 0x"
      << std::hex << std::setfill('0')
      << std::setw(4) << status()
      << std::dec << std::setfill(' ')
      << std::endl;
  }

 private:
  uint64_t _word[2];
};

}

#endif
