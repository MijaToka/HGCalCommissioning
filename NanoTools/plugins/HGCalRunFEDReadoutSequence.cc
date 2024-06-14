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

//
// class declaration
//

class HGCalRunFEDReadoutSequence : public edm::one::EDProducer<edm::EndRunProducer> {
public:
  //
  HGCalRunFEDReadoutSequence(edm::ParameterSet const &iConfig)
      : tableName_(iConfig.getParameter<std::string>("tableName")), moduleTkn_(esConsumes<edm::Transition::EndRun>()) {
    produces<nanoaod::FlatTable, edm::Transition::EndRun>(tableName_);
  }

  //
  ~HGCalRunFEDReadoutSequence() override {}

  //
  static void fillDescriptions(edm::ConfigurationDescriptions &descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<std::string>("tableName", "HGCFEDReadout");
    descriptions.addWithDefaultLabel(desc);
  }

  //std::shared_ptr<int> globalBeginRun(edm::Run const &, edm::EventSetup const &) const override { return nullptr; }

  //void globalEndRun(edm::Run const &, edm::EventSetup const &) override {}

  void produce(edm::Event &iEvent, const edm::EventSetup &iSetup) override {}

  void endRunProduce(edm::Run &iRun, const edm::EventSetup &iSetup) final {
    //convert module mapping to rows of a flat table
    auto const &modules = iSetup.getData(moduleTkn_);
    const size_t nmodules = modules.view().metadata().size();
    std::vector<uint32_t> fed(nmodules), seq(nmodules), modtype(nmodules), celltype(nmodules);
    for (size_t i = 0; i < nmodules; i++) {
      auto imod = modules.view()[i];
      fed[i] = imod.fedid();
      seq[i] = imod.econdidx();
      modtype[i] = imod.typeidx();
      celltype[i] = imod.celltype();
    }

    //the table
    auto out = std::make_unique<nanoaod::FlatTable>(nmodules, tableName_, false);
    out->addColumn<uint32_t>("FED", fed, "FED ID index");
    out->addColumn<uint32_t>("Seq", seq, "Module sequence in readout");
    out->addColumn<uint32_t>("ModuleType", modtype, "Module type");
    out->addColumn<uint32_t>("CellType", celltype, "Cell type");

    //put in the run
    iRun.put(std::move(out), tableName_);
  }

protected:
  std::string tableName_;
  edm::ESGetToken<hgcal::HGCalMappingModuleParamHostCollection, HGCalElectronicsMappingRcd> moduleTkn_;
};

//define this as a plug-in
#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(HGCalRunFEDReadoutSequence);
