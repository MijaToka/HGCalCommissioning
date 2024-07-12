import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

#this should still be moved to a more central place HGCalCommissioning/Configuration ?
from Geometry.HGCalMapping.hgcalmapping_cff import customise_hgcalmapper
def customise_hgcalmapper_test(process):
    return customise_hgcalmapper(process,
                                 modules='HGCalCommissioning/SystemTestEventFilters/data/ModuleMaps/modulelocator_test_2mods.txt')

# build NANO task
nanoMetadata = cms.EDProducer("UniqueStringProducer",
                              strings = cms.PSet( tag = cms.string("untagged") ) )
hgcRunFEDReadoutTable = cms.EDProducer("HGCalRunFEDReadoutSequence")
hgCalNanoTable = cms.EDProducer("HGCalNanoTableProducer")
hgcSysValNanoTask = cms.Task(nanoMetadata,hgcRunFEDReadoutTable, hgCalNanoTable)
