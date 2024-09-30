#ifndef HGCalCommissioning_SystemTestEventFilters_HGCalTestSystemMetaData_h
#define HGCalCommissioning_SystemTestEventFilters_HGCalTestSystemMetaData_h

#include <cstdint>

class HGCalTestSystemMetaData {
public:

  enum TestSystemMetaDataFlags { VALID=0, EVMISMATCH=1, BXMISMATCH=2, ORBITMISMATCH=4, UKNOWN=32 };
  
  HGCalTestSystemMetaData(int trigType, int trigSubType, int trigTime, int trigWidth)
      : trigType_(trigType),
        trigSubType_(trigSubType),
        trigTime_(trigTime),
        trigWidth_(trigWidth),
        trigBlockFlags_(TestSystemMetaDataFlags::VALID) {
  }

  HGCalTestSystemMetaData() : HGCalTestSystemMetaData(0, 0, 0, 0) { setTrigBlockFlags(TestSystemMetaDataFlags::UKNOWN); }

  void setTrigBlockFlags(int flags) { trigBlockFlags_=flags; }
  
  ~HGCalTestSystemMetaData() {}
  
  uint32_t trigType_, trigSubType_;
  uint32_t trigTime_;
  uint32_t trigWidth_;
  uint32_t trigBlockFlags_;
};

#endif
