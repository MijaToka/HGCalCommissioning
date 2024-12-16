#ifndef  HGCalCommissioning_HGCalRawToDigiTrigger_interface_HGCalModuleIndexerTrigger_h
#define  HGCalCommissioning_HGCalRawToDigiTrigger_interface_HGCalModuleIndexerTrigger_h

#include <cstdint>
#include <vector>
#include <map>
#include <algorithm>  // for std::min
#include <utility>    // for std::pair, std::make_pair
#include <iterator>   // for std::next and std::advance

#include "FWCore/Utilities/interface/Exception.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"

class HGCalModuleIndexerTrigger {
public:
  HGCalModuleIndexerTrigger() {}
  HGCalModuleIndexerTrigger(uint32_t layerOffset, uint32_t modOffset) {
    layerOffset_= layerOffset; 
    modOffset_=modOffset;
  }
  HGCalModuleIndexerTrigger(uint32_t layerOffset, uint32_t modOffset, uint32_t maxLayer, uint32_t maxMod, uint32_t maxCh) {
    layerOffset_= layerOffset; 
    modOffset_=modOffset;
    maxLayer_=maxLayer;
    maxMod_=maxMod;
    maxCh_=maxCh;
  }

  ~HGCalModuleIndexerTrigger() = default;

  uint32_t getIndexForModuleData(uint32_t layer, uint32_t modid, uint32_t chidx) const {
    return layer*layerOffset_ + modid*modOffset_ + chidx;
  };

  uint32_t getModuleLayer(uint32_t index) {
    return index/layerOffset_;
  }

  uint32_t getModuleIdx(uint32_t index) {
    uint32_t layer = index/layerOffset_;
    uint32_t modid = (index%layerOffset_)/modOffset_;
    return modid;
  }

  uint32_t getChannelIdx(uint32_t index) {
    return index%modOffset_;
  }

  uint32_t getLayerOffset() const { return layerOffset_; }
  uint32_t getModOffset() const { return modOffset_; }
  uint32_t getMaxLayer() const { return maxLayer_; }
  uint32_t getMaxMod() const { return maxMod_; }
  uint32_t getMaxCh() const { return maxCh_; }

  uint32_t getMaxIndex() const { return maxLayer_*layerOffset_+maxMod_*modOffset_+maxCh_; }

  void setLayerOffset(uint32_t layerOffset) { layerOffset_ = layerOffset; }
  void setModOffset(uint32_t modOffset) { modOffset_ = modOffset; }
  void setMaxLayer(uint32_t maxLayer) { maxLayer_ = maxLayer; }
  void setMaxMod(uint32_t maxMod) { maxMod_ = maxMod; }
  void setMaxCh(uint32_t maxCh) { maxCh_ = maxCh; }

private:
  // TODO: replace with proper mapping
  uint32_t layerOffset_ = 1000;
  uint32_t modOffset_ = 100;
  uint32_t maxLayer_ = 10;
  uint32_t maxMod_ = 10;
  uint32_t maxCh_ = 100;
};

#endif