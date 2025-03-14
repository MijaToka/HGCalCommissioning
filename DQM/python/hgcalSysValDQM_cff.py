import FWCore.ParameterSet.Config as cms


def customizeSysValDQM(process, runNumber : int = 123456, MinimumEvents : int = 5000, PrescaleFactor=5000):

    #DQM modules
    process.load('HGCalCommissioning.DQM.hgCalSysValDigisClient_cfi')
    process.hgCalSysValDigisClient.MinimumEvents = MinimumEvents
    process.hgCalSysValDigisClient.PrescaleFactor = PrescaleFactor
    process.hgCalSysValDigisClient.SkipTriggerDQM = True
    process.load('HGCalCommissioning.DQM.hgCalSysValDigisHarvester_cfi')

    #DQM saver
    process.DQMStore = cms.Service("DQMStore")
    process.load("DQMServices.FileIO.DQMFileSaverOnline_cfi")
    process.dqmSaver.tag = 'HGCAL'
    process.dqmSaver.runNumber = runNumber

    process.dqmPath = cms.Path(process.hgCalSysValDigisClient+
                               process.hgCalSysValDigisHarvester+
                               process.dqmSaver)

    return process
