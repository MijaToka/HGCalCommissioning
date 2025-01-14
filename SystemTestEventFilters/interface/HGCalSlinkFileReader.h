#ifndef HGCalCommissioning_SystemTestEventFilters_HGCalSlinkFileReader_h
#define HGCalCommissioning_SystemTestEventFilters_HGCalSlinkFileReader_h

#include "HGCalTestSystemMetaData.h"
#include "HGCalCommissioning/SystemTestEventFilters/interface/HGCalSlinkFromRaw/FileReader.h"

#include <vector>
#include <string>

namespace hgcal {

  class SlinkFileReader {
  public:
    SlinkFileReader(const std::vector<std::string> &filelist, unsigned fedId);

    const hgcal_slinkfromraw::RecordRunning *nextEvent();

    /**
       @short if the scintillator block id is <0 then the metadata is filled with trivial information, otherwise the method tries to decode the trigger event
     */
    void readTriggerData(HGCalTestSystemMetaData &metaData,
                         const hgcal_slinkfromraw::RecordRunning *rTrgEvent,
                         unsigned num_blocks = 6,
                         int scintillator_block_id = 5);

    static constexpr unsigned kTrigIdOffset = 10000;

  private:
    const std::vector<std::string> inputfiles_;
    const unsigned fedId_;

    hgcal_slinkfromraw::FileReader fileReader_;
    hgcal_slinkfromraw::RecordT<4095> *record_;

    bool firstEvent_ = true;
    unsigned ifile_ = 0;
  };

}  // namespace hgcal

#endif
