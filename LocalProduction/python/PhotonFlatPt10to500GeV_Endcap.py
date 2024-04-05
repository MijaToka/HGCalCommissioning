import FWCore.ParameterSet.Config as cms

generator = cms.EDFilter("Pythia8PtGun",
                          PGunParameters = cms.PSet(
                          AddAntiParticle = cms.bool(False),
                          MinEta = cms.double(1.5),
                          MaxEta = cms.double(3.0),
                          MinPhi          = cms.double(-3.14159265359),
                          MaxPhi          = cms.double(3.14159265359),
                          MinPt           = cms.double(10.0),
                          MaxPt           = cms.double(500.0),
                          ParticleID      = cms.vint32(22)
                          ),
                          PythiaParameters = cms.PSet(parameterSets = cms.vstring()),
                          Verbosity = cms.untracked.int32(0)
                        )
                        

ProductionFilterSequence  = cms.Sequence(generator)
