# Performance measurements

Performance tools. Presented in https://indico.cern.ch/event/1507632/#2-hackathon-report-raw-data-ha

To measure the RAW -> DIGI step with the unpacker, use [`Performance/test/step_RAW2DIGI.py`](Performance/test/step_RAW2DIGI.py)::
```shell
# RAW -> DIGI
# - Start from binary TB data
# - Process all events
cmsRun -j FwkJobReport_RAW2DIGI.xml $CMSSW_BASE/src/HGCalCommissioning/Performance/test/step_RAW2DIGI.py run=1727035822 lumi=1 era=SepTB2024/v3 files=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/BeamTestSep/HgcalBeamtestSep2024/Relay1727035819/Run1727035822_Link1_File0000000000.bin inputTrigFiles=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/BeamTestSep/HgcalBeamtestSep2024/Relay1727035819/Run1727035822_Link0_File0000000000.bin output=RAW2DIGI.root

# RAW -> DIGI
# - Start from binary TB data
# - Process 10000 events
# - Naively scale up system (number of FEDs) by x1, x30, x300
# - Run with nthreads = 1, 2, 4, 8
for s in 1 30 100; do for n in 1 2 4 8; do cmsRun -j FwkJobReport_RAW2DIGI.xml $CMSSW_BASE/src/HGCalCommissioning/Performance/test/step_RAW2DIGI.py run=1727035822 lumi=1 era=SepTB2024/v3 files=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/BeamTestSep/HgcalBeamtestSep2024/Relay1727035819/Run1727035822_Link1_File0000000000.bin inputTrigFiles=/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/BeamTestSep/HgcalBeamtestSep2024/Relay1727035819/Run1727035822_Link0_File0000000000.bin output=RAW2DIGI_scale${s}.root maxEvents=10000 fromFEDRaw=False scaleFEDs=$s nthreads=$n logtag="_try1"; done; done
```

To start from FEWRawData instead, use the `fromFEDRaw=True` option:
```shell
# FEDRAW -> DIGI
# - Start from FEDRawData record in RAW2DIGI.root from previous job
# - Naively scale up system (number of FEDs) by x1, x30, x300
# - Run with nthreads = 1, 2, 4, 8
for s in 1 30 100; do for n in 1 2 4 8; do cmsRun -j FwkJobReport_FEDRAW2DIGI.xml $CMSSW_BASE/src/HGCalCommissioning/Performance/test/step_RAW2DIGI.py run=1727035822 lumi=1 era=SepTB2024/v3 files=file:RAW2DIGI.root output=RAW2DIGI_scale${s}.root maxEvents=10000 fromFEDRaw=True scaleFEDs=$s nthreads=$n logtag="_try1"; done; done
```

To measure the DIGI -> RECO step with the Alpaka kernels, use [`Performance/test/step_RECO.py`](Performance/test/step_RECO.py):
* If `"onlyin" in logtag`: input-only
* If `"noout" in logtag`: input+kernels (no out)
* If `"fullchain" in logtag`: input+kernels+ouput
```shell
# DIGI -> RECO
# - Start from RAW2DIGI_scale*_numEvent10000.root from previous job
# - Naively scale up system (number of FEDs) by x1, x30, x300
# - Run input-only, input+kernels (no out), input+kernels+ouput
# - Run with nthreads = 1, 2, 4, 8
for s in 1 30 100; do for t in onlyin noout fullchain; do for n in 1 2 4 8; do cmsRun -j FwkJobReport_RECO.xml $CMSSW_BASE/src/HGCalCommissioning/Performance/test/step_RECO.py era=SepTB2024/v3 run=1727035822 files=file:RAW2DIGI_scale${s}_numEvent10000.root gpu=false output=RECO_scale${s}_${t}.root maxEvents=10000 scaleFEDs=$s nthreads=$n logtag="_${t}_try1"; done; done; done
```

# Plotting

Plot throughput with [`plotThroughput.py`](python/plotThroughput.py):
```shell
# PLOT comparing nthreads
for s in 1 30 100; do plotThroughput.py ThroughputService_FEDRAW2DIGI_scale${s}_nthread?_try1.log; done
for s in 1 30 100; do for T in fullchain noout onlyin; do plotThroughput.py ThroughputService_RECO_scale${s}_nthread?_${T}_try1.log; done; done

# PLOT comparing scales
for n in 1 2 4 8; do plotThroughput.py ThroughputService_FEDRAW2DIGI_scale{1,30,100}_nthread${n}_try1.log; done
for n in 1 2 4 8; do for T in fullchain noout onlyin; do plotThroughput.py ThroughputService_RECO_scale{1,30,100}_nthread${n}_${T}_try1.log; done; done
```

## Examples
* FEDRAW → DIGI: [threads](https://ineuteli.web.cern.ch/ineuteli/hgcal/perf/?match=_FEDRAW2DIGI_scale), [modules](https://ineuteli.web.cern.ch/ineuteli/hgcal/perf/?match=_FEDRAW2DIGI_nthread)
* RECO → DIGI: [threads](https://ineuteli.web.cern.ch/ineuteli/hgcal/perf/?match=_RECO_scale), [modules](https://ineuteli.web.cern.ch/ineuteli/hgcal/perf/?match=_RECO_nthread)