import FWCore.ParameterSet.Config as cms

# generate single nu_mu events
generator = cms.EDProducer("FlatRandomEGunProducer",
                           AddAntiParticle = cms.bool(True),
                           PGunParameters = cms.PSet(
                               MinEta = cms.double(1.999),
                               MaxEta = cms.double(2.001),
                               MinE = cms.double(1),
                               MaxE = cms.double(500),
                               MaxPhi = cms.double(3.14159265359),
                               MinPhi = cms.double(-3.14159265359),
                               PartID = cms.vint32(211)
                           ),
                           Verbosity = cms.untracked.int32(0),
                           firstRun = cms.untracked.uint32(1),
                           psethack = cms.string('multiple K-longs flat pT at eta=2.0')
)
