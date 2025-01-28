import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

# build NANO task
nanoMetadata = cms.EDProducer("UniqueStringProducer",
                              strings = cms.PSet( tag = cms.string("untagged") ) )
hgcRunFEDReadoutTable = cms.EDProducer("HGCalRunFEDReadoutSequence")
hgCalNanoTable = cms.EDProducer("HGCalNanoTableProducer")
hgcSysValNanoTask = cms.Task(nanoMetadata,hgcRunFEDReadoutTable, hgCalNanoTable)

