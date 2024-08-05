import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing

process = cms.Process("SYSVALDQM")

from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.register('modules',
                 "HGCalCommissioning/Configuration/data/ModuleMaps/modulelocator_B27v1.txt",
                 mytype=VarParsing.varType.string,                 
                 info="Path to module mapper. Absolute, or relative to CMSSW src directory")
options.register('runNumber',
                 123456,
                 mytype=VarParsing.varType.int,                 
                 info="Run number for DQM saver")
options.parseArguments()

process.source = cms.Source("PoolSource",
   fileNames = cms.untracked.vstring(*options.files)
)
process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(options.maxEvents) )

#message logger
process.load('Configuration.EventContent.EventContent_cff')
process.MessageLogger.cerr.FwkReport.reportEvery = 50000

#load geometry
process.load('Configuration.Geometry.GeometryExtended2026D99Reco_cff')
from Geometry.HGCalMapping.hgcalmapping_cff import customise_hgcalmapper
process=customise_hgcalmapper(process,modules=options.modules)

#load DQM
from HGCalCommissioning.DQM.hgcalSysValDQM_cff import customizeSysValDQM
process = customizeSysValDQM(process, options.runNumber)

process.p = cms.Schedule(process.dqmPath)
