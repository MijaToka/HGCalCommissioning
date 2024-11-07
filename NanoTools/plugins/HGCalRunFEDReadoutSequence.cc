// -*- C++ -*-
//
// Package:    HGCalCommissioning/NanoTools
// Class:      HGCalRunFEDReadoutSequence
//
/**\class HGCalRunFEDReadoutSequence HGCalRunFEDReadoutSequence.cc HGCalCommissioning/NanoTools/plugins/HGCalRunFEDReadoutSequence.cc

 Description: [one line class summary]

 Implementation:
     [Notes on implementation]
*/
//
// Original Author:  Pedro Vieira De Castro Ferreira Da Silva
//         Created:  Fri, 24 May 2024 09:09:11 GMT
//
//

// system include files
#include <memory>
#include <algorithm>

// user include files
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/Framework/interface/Run.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "PhysicsTools/NanoAOD/interface/SimpleFlatTableProducer.h"
#include "CondFormats/DataRecord/interface/HGCalElectronicsMappingRcd.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingParameterHostCollection.h"
#include "CondFormats/HGCalObjects/interface/HGCalMappingModuleIndexer.h"

//
// class declaration
//

class HGCalRunFEDReadoutSequence : public edm::one::EDProducer<edm::EndRunProducer> {
public:
  //
  HGCalRunFEDReadoutSequence(edm::ParameterSet const &iConfig)
      : tableName_(iConfig.getParameter<std::string>("tableName")),
        typeCodeTableName_(iConfig.getParameter<std::string>("typeCodeTableName")), 
        moduleTkn_(esConsumes<edm::Transition::EndRun>()),
        moduleIndexTkn_(esConsumes<edm::Transition::EndRun>()) {
    
    produces<nanoaod::FlatTable,edm::Transition::EndRun>(tableName_);
    produces<nanoaod::FlatTable,edm::Transition::EndRun>(typeCodeTableName_);
    
  }

  //
  ~HGCalRunFEDReadoutSequence() override {}

  //
  static void fillDescriptions(edm::ConfigurationDescriptions &descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<std::string>("tableName",         "HGCReadout");
    desc.add<std::string>("typeCodeTableName", "HGCTypeCodes");
    descriptions.addWithDefaultLabel(desc);
  }

  //std::shared_ptr<int> globalBeginRun(edm::Run const &, edm::EventSetup const &) const override { return nullptr; }

  //void globalEndRun(edm::Run const &, edm::EventSetup const &) override {}

  void produce(edm::Event &iEvent, const edm::EventSetup &iSetup) override {}

  void endRunProduce(edm::Run &iRun, const edm::EventSetup &iSetup) final {

    //std::cout << "HGCalRunFEDReadoutSequence::endRunProduce" << std::endl;

    //get module info and module indexer
    auto const &modules = iSetup.getData(moduleTkn_);
    auto const &moduleIndex = iSetup.getData(moduleIndexTkn_);

    //built the table
    //track the typecodes corresponding to each index
    uint32_t nmodules = moduleIndex.getMaxModuleSize();
    std::vector<uint32_t> fed(nmodules), seq(nmodules),plane(nmodules), i1(nmodules), i2(nmodules), nErx(nmodules);    
    std::vector<bool> isSiPM(nmodules), zside(nmodules);
    typedef std::pair<std::string, std::vector<uint32_t> > TypeCode2Idx_t;
    std::vector<TypeCode2Idx_t> typeCodeTreeIndices;
    uint32_t idx(0);
    for(auto it : moduleIndex.getTypecodeMap() ) {

      std::string typecode = it.first;
      std::replace( typecode.begin(), typecode.end(), '-', '_');
      typeCodeTreeIndices.push_back( TypeCode2Idx_t(typecode, {idx} ) );

      fed[idx] = it.second.first;
      seq[idx] = it.second.second;
      uint32_t modIdx = moduleIndex.getTypeForModule(fed[idx], seq[idx]);
      auto imod = modules.view()[modIdx];
      isSiPM[idx] = imod.isSiPM();
      zside[idx] = imod.zside();
      plane[idx] = imod.plane();
      i1[idx] = imod.i1();
      i2[idx] = imod.i2();
      nErx[idx] = moduleIndex.getMaxERxSize(fed[idx], seq[idx]);
      idx++;
    }
    
    //the readout table
    auto out_readout = std::make_unique<nanoaod::FlatTable>(nmodules, tableName_, false);
    out_readout->addColumn<uint32_t>("FED", fed, "FED ID index");
    out_readout->addColumn<uint32_t>("Seq", seq, "Module sequence in readout");
    out_readout->addColumn<bool>("IsSiPM", isSiPM, "Is SiPM-on-tile?");
    out_readout->addColumn<bool>("PositiveEndcap", zside, "Positive endcap?");
    out_readout->addColumn<uint32_t>("Layer", plane, "Layer number");
    out_readout->addColumn<uint32_t>("i1", i1, "Location index 1 (u or i-ring)");
    out_readout->addColumn<uint32_t>("i2", i2, "Location index 2 (v or i-phi)");
    out_readout->addColumn<uint32_t>("nErx", nErx, "nErx");
    iRun.put(std::move(out_readout), tableName_);

    //the type codes for each entry in the table above
    auto out_typecodes = std::make_unique<nanoaod::FlatTable>(1, typeCodeTableName_, false);
    for(auto it : typeCodeTreeIndices)
      out_typecodes->addColumn<uint32_t>(it.first, it.second, "Typecode index");
    iRun.put(std::move(out_typecodes),typeCodeTableName_);
  }

protected:
  std::string tableName_,typeCodeTableName_;
  edm::ESGetToken<hgcal::HGCalMappingModuleParamHostCollection, HGCalElectronicsMappingRcd> moduleTkn_;
  edm::ESGetToken<HGCalMappingModuleIndexer, HGCalElectronicsMappingRcd> moduleIndexTkn_;
};

//define this as a plug-in
#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(HGCalRunFEDReadoutSequence);
