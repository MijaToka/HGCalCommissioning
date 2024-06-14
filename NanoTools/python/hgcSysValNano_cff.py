import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var

#FIXME: these customises should be elsewhere
def customise_elemapper(process) :

    modules='HGCalCommissioning/SystemTestEventFilters/data/ModuleMaps/modulelocator_test_2mods.txt'
    sicells='Geometry/HGCalMapping/data/CellMaps/WaferCellMapTraces.txt'
    sipmcells='Geometry/HGCalMapping/data/CellMaps/channels_sipmontile.hgcal.txt'
    
    process.load('Geometry.HGCalMapping.hgCalMappingESProducer_cfi')
    process.hgCalMappingESProducer.modules = cms.FileInPath(modules)
    process.hgCalMappingESProducer.si = cms.FileInPath(sicells)
    process.hgCalMappingESProducer.sipm = cms.FileInPath(sipmcells)
    process.load('Configuration.StandardSequences.Accelerators_cff')
    process.hgCalMappingCellESProducer = cms.ESProducer('hgcal::HGCalMappingCellESProducer@alpaka',
                                                        filelist=cms.vstring(sicells,sipmcells),
                                                        cellindexer=cms.ESInputTag('') )
    process.hgCalMappingModuleESProducer = cms.ESProducer('hgcal::HGCalMappingModuleESProducer@alpaka',
                                                          filename=cms.FileInPath(modules),
                                                          moduleindexer=cms.ESInputTag('') )
    return process

def customize_nanoOutput(process):
    process.NANOAODoutput.outputCommands +=  ["keep nanoaodFlatTable_*_*_*"]
    process.NANOAODoutput.compressionAlgorithm = 'ZSTD'
    process.NANOAODoutput.compressionLevel = 5
    process.MessageLogger.cerr.FwkReport.reportEvery = 50000
    process.options.wantSummary = True
    return process


#build NANO task
hgcRunFEDReadoutTable = cms.EDProducer("HGCalRunFEDReadoutSequence")
hgCalTB2023TableProducer = cms.EDProducer("HGCalTB2023TableProducer")
hgcSysValNanoTask = cms.Task(hgcRunFEDReadoutTable,hgCalTB2023TableProducer)
