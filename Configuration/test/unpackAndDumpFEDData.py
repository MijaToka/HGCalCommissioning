import FWCore.ParameterSet.Config as cms

"""
This cfg can be used to inspect the contents of an event for a single FED.
It will print the event to the screen in hexadecimal format (64b word).
It can be run as

```
cmsRun test/unpackAndDumpFEDData.py \
      files=/data/hgcalrd/hgcbeamtestpc/HgcalBeamtest2024_TEST/Relay1725175194/Run1725175200_Link1_File0000000000.bin \
      inputTrigFiles=/data/hgcalrd/hgcbeamtestpc/HgcalBeamtest2024_TEST/Relay1725175194/Run1725175200_Link0_File0000000000.bin \
      fedId=0 >& output.log
```
or

```
cmsRun test/unpackAndDumpFEDData.py \
      files=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/Test/Run1726926104/126d5f6a-7820-11ef-9b0c-b8ca3af74182/prompt/RAW2DIGI_1726926107_32.root \
      fedId=0 >& output.log  
```

The log file will contain the event printout.
"""

# USER OPTIONS
from FWCore.ParameterSet.VarParsing import VarParsing
options = VarParsing('standard')
options.register('inputTrigFiles',[],
                 VarParsing.multiplicity.list, VarParsing.varType.string, "input Trigger link file")
options.register('fedId',0,
                 VarParsing.multiplicity.singleton, VarParsing.varType.int, "fed ID")
options.register('skipEvents',0,
                 VarParsing.multiplicity.singleton, VarParsing.varType.int, "skip this number of events from the start of the files")
options.parseArguments()
options.maxEvents = max(1,options.maxEvents)

# INIT
process = cms.Process('RAW')

# INPUT
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
if '.bin' in options.files[0]:
    process.source = cms.Source(
        "HGCalSlinkFromRawSource",
        isRealData=cms.untracked.bool(True),
        runNumber=cms.untracked.uint32(1),
        firstLumiSection=cms.untracked.uint32(1),
        maxEventsPerLumiSection=cms.untracked.int32(-1),
        useL1EventID=cms.untracked.bool(True),
        fedIds=cms.untracked.vuint32([options.fedId]),
        inputs=cms.untracked.vstring(*options.files),
        trig_inputs=cms.untracked.vstring(*options.inputTrigFiles),
        skipEvents = cms.untracked.uint32(options.skipEvents),
    )
    process.rawDataCollector = cms.EDAlias(
        source=cms.VPSet(
            cms.PSet(type=cms.string('FEDRawDataCollection'))
        )
    )
else:
    process.source = cms.Source("PoolSource",
                                fileNames = cms.untracked.vstring(*options.files)
                                )

process.dumpFRD = cms.EDAnalyzer("DumpFEDRawDataProduct",
                              label=cms.untracked.InputTag('rawDataCollector'),
                              feds=cms.untracked.vint32(options.fedId),
                              dumpPayload=cms.untracked.bool(True)
                              )

process.p = cms.Path( process.dumpFRD )
