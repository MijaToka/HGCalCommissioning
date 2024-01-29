# hgcal-comm

This repository holds CMSSW-based tools for HGCAL commissioning. The aim is to collect producers/analyzers etc. which are used to assist in the commissioning phase of HGCAL but which do not necessarily need to be present in release. 
The code is kept as simple and up-to-date as possible such that one can compile it on top of the latest release by doing

```
git checkout https://gitlab.cern.ch/hgcal-dpg/hgcal-comm.git HGCalCommissioning
```

A brief description of the sub-directories is made in the following table

| Sub-directory    | Contents |
| -------- | ------- |
| SystemTestEventFilters  | Event filters to convert system test data to raw DIGIs |
| | |