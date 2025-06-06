import FWCore.ParameterSet.Config as cms
from Configuration.Generator.Pythia8CommonSettings_cfi import *
#from Configuration.Generator.Pythia8CUEP8M1Settings_cfi import *
from Configuration.Generator.MCTunes2017.PythiaCP5Settings_cfi import *

generator = cms.EDFilter("Pythia8GeneratorFilter",
                         pythiaHepMCVerbosity = cms.untracked.bool(False),
                         maxEventsToPrint = cms.untracked.int32(0),
                         pythiaPylistVerbosity = cms.untracked.int32(0),
                         filterEfficiency = cms.untracked.double(1.0),
                         comEnergy = cms.double(14000.0),
                         PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        #pythia8CUEP8M1SettingsBlock,
        pythia8CP5SettingsBlock,
        processParameters = cms.vstring(
            'Top:gg2ttbar = on ',
            'Top:qqbar2ttbar = on ',
            '6:m0 = 175 ',
             'SigmaTotal:mode = 0',
            'SigmaTotal:sigmaEl = 21.89',
              'SigmaTotal:sigmaTot = 100.309',
              'PDF:pSet=LHAPDF6:NNPDF31_nnlo_as_0118',
            ),
        parameterSets = cms.vstring('pythia8CommonSettings',
                                    #'pythia8CUEP8M1Settings',
                                    'pythia8CP5Settings',
                                    'processParameters',
                                    )
        )
                         )
ProductionFilterSequence = cms.Sequence(generator)