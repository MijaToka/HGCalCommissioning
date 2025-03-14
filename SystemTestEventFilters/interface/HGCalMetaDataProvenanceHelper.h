#ifndef HGCalCommissioning_SystemTestEventFilters_HGCalMetaDataProvenanceHelper_h
#define HGCalCommissioning_SystemTestEventFilters_HGCalMetaDataProvenanceHelper_h

#include "DataFormats/Provenance/interface/ProcessHistoryRegistry.h"
#include "DataFormats/Provenance/interface/ProductRegistry.h"
#include "FWCore/Utilities/interface/GetPassID.h"
#include "FWCore/Utilities/interface/TypeID.h"
#include "FWCore/Reflection/interface/TypeWithDict.h"
#include "FWCore/Version/interface/GetReleaseVersion.h"
#include "DataFormats/Provenance/interface/ProcessHistoryID.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

/**
   @short auxiliary structure to build the provenance for metadata based on FWCore/Sources/interface/DaqProvenanceHelper.h
 */
class HGCalMetaDataProvenanceHelper {
  
public:
  
  HGCalMetaDataProvenanceHelper(edm::TypeID const& metaDataType)
    : constProductDescription_(makeDescription(metaDataType, "HGCalTestSystemMetaData", "HGCalTestSystemMetaData", "HGCalSlinkFromRawSource")),
      processParameterSet_() {
    dummyProvenance_=edm::ProductProvenance(constProductDescription_.branchID());

    std::string const& moduleLabel = constProductDescription_.moduleLabel();
    std::string const& processName = constProductDescription_.processName();
    typedef std::vector<std::string> vstring;
    vstring empty;

    vstring modlbl;
    modlbl.reserve(1);
    modlbl.push_back(moduleLabel);
    processParameterSet_.addParameter("@all_sources", modlbl);

    edm::ParameterSet triggerPaths;
    triggerPaths.addParameter<vstring>("@trigger_paths", empty);
    processParameterSet_.addParameter<edm::ParameterSet>("@trigger_paths", triggerPaths);

    edm::ParameterSet pseudoInput;
    pseudoInput.addParameter<std::string>("@module_edm_type", "Source");
    pseudoInput.addParameter<std::string>("@module_label", moduleLabel);
    processParameterSet_.addParameter<edm::ParameterSet>(moduleLabel, pseudoInput);

    processParameterSet_.addParameter<vstring>("@all_esmodules", empty);
    processParameterSet_.addParameter<vstring>("@all_esprefers", empty);
    processParameterSet_.addParameter<vstring>("@all_essources", empty);
    processParameterSet_.addParameter<vstring>("@all_loopers", empty);
    processParameterSet_.addParameter<vstring>("@all_modules", empty);
    processParameterSet_.addParameter<vstring>("@end_paths", empty);
    processParameterSet_.addParameter<vstring>("@paths", empty);
    processParameterSet_.addParameter<std::string>("@process_name", processName);
    processParameterSet_.registerIt();
  }
  
  inline static edm::ProductDescription makeDescription(edm::TypeID const& rawDataType, std::string const& collectionName, std::string const& friendlyName, std::string const& sourceLabel) {
    edm::ProductDescription desc(edm::InEvent, "rawMetaDataCollector", "LHC", collectionName, friendlyName, "", edm::TypeWithDict(rawDataType.typeInfo()), false);
    desc.setIsProvenanceSetOnRead();
    return desc;
  }
  
  inline edm::ProductProvenance const& dummyProvenance() const { return dummyProvenance_; }
  
  inline edm::ProductDescription const& productDescription() const { return constProductDescription_; }
  
  inline edm::ProcessHistoryID init(edm::ProductRegistry& productRegistry, edm::ProcessHistoryRegistry& processHistoryRegistry) const {

    productRegistry.copyProduct(constProductDescription_);
    
    edm::ProcessHistory ph;
    edm::HardwareResourcesDescription hwdesc;
    ph.emplace_back(constProductDescription_.processName(), processParameterSet_.id(), edm::getReleaseVersion(), hwdesc);
    processHistoryRegistry.registerProcessHistory(ph);
    return ph.setProcessHistoryID();
  }
  
private:
  edm::ProductDescription const constProductDescription_;
  edm::ProductProvenance dummyProvenance_;
  edm::ParameterSet processParameterSet_;
};


#endif
