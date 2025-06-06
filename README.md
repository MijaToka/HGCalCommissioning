# HGCAL commissioning tools [![pipeline status](https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/badges/master/pipeline.svg)](https://gitlab.cern.ch/hgcal-dpg/hgcal-comm/-/commits/master) [![documentation](https://img.shields.io/badge/docs-hgcaldocs-success)](https://hgcaldocs.web.cern.ch/RawDataHandling/intro/)

This repository holds CMSSW-based tools for HGCAL commissioning using CMSSW >=14x.

The aim is to collect producers/analyzers etc. which are used to assist in the commissioning phase of HGCAL but which do not necessarily need to be present in release. 

The code is kept as simple and up-to-date as possible such that one can compile it on top of the latest release by doing

```
git clone https://gitlab.cern.ch/hgcal-dpg/hgcal-comm.git HGCalCommissioning
```

If you are only interested in a specific tool you can do a sparse checkout.
An example is given in [here](LocalProduction/test/README.md).


A brief description of the sub-directories is made in the following table

| Sub-directory    | Contents |
| -------- | ------- |
| SystemTestEventFilters  | Event filters to convert system test data to raw DIGIs |
| LocalCalibration  | Analysis scripts to produce level-0 calibration quantities/cond files |
| Configuration | standard workflows (CMSSW cfg and snakemake files) and module maps |
| NanoTools | Customized NANO for DPG purposes |
| DQM | Implement here that plot that everyone wants to see |
| LocalProduction | Some basic scripts to produce samples with standard CMSSW |

This repository is complemented by [hgcal-dpg](https://gitlab.cern.ch/hgcal-dpg/calibrations) which contains the calibration files for the offline.

More info @ [hgcaldocs website](https://hgcaldocs.web.cern.ch)

