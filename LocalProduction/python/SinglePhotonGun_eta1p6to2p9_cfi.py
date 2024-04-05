import FWCore.ParameterSet.Config as cms

# generate single nu_mu events
generator = cms.EDProducer("FlatRandomEGunProducer",
                           AddAntiParticle = cms.bool(True),
                           PGunParameters = cms.PSet(
                               MinEta = cms.double(1.599),
                               MaxEta = cms.double(2.901),
                               MinE = cms.double(1),
                               MaxE = cms.double(500),
                               MaxPhi = cms.double(3.14159265359),
                               MinPhi = cms.double(-3.14159265359),
                               PartID = cms.vint32(22)
                           ),
                           Verbosity = cms.untracked.int32(0),
                           firstRun = cms.untracked.uint32(1),
                           psethack = cms.string('multiple photons flat energy at 1.6<eta<2.9')
)
