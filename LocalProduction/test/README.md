# Local production scripts for HGCAL samples

## Installation

Install on top of  CMSSW>13x with

```
git clone --no-checkout https://gitlab.cern.ch/hgcal-dpg/hgcal-comm.git HGCalCommissioning
cd HGCalCommissioning
git sparse-checkout set LocalProduction
git reset --hard HEAD
```

## Local production scripts

These scripts run with HTCondor at CERN. The base script can be run as

```
sh test/runLocalGeneration.sh -c $CMSSW_BASE -m mcm_fragment -n #events -o output_file
```

It will fetch the mcm_fragment and run the cmsDriver commands to produce the GEN-SIM-DIGI-RECO file.
Alternatively mcm_fragment can be an already existing cfi in a sub-directory.
Some extra options are:

* `-s/--simonly` stops the generation at the GEN-SIM tier if =1
* `-p/--pileup_input` the location of the pileup/min. bias files to use
* `-l/--avg_pileup` average pileup (140, 200, not all values are possible)
* `-a/--aged` the aged scenario to apply
* `-b/--bias` biasing condition at gen to apply, based on the definitions in python/endcapbias_cfi.py

Geometry, conditions era are hardcoded at the start of the script for the moment. Edit as needed.

The script above can be dispatched with condor by using:

```
condor_submit condor_pgun.sub
```

A condor submission file for min. bias sim only (`condor_minbias.sub`) and with pileup (`condor_pu.sub`) are also available.
In all cases edit before submitting :)