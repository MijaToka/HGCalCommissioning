#ifndef HGCalCommissioning_DQM_interface_HGCalSysValDQMCommon_h
#define HGCalCommissioning_DQM_interface_HGCalSysValDQMCommon_h

#include <string>

namespace hgcal {

  namespace dqm {

    // @short an enum for the sums monitored per channel of a module
    enum SumIndices_t { NCM=0, SUMCM, NADC, SUMADC, SUMADC2, NADCM1, SUMADCM1, DELTAADC, NTOA, SUMTOA, NTOT, SUMTOT, LASTINDEX};

    // @short label for SumIndices_t enum (ROOT format)
    std::string getLabelForSumIndex(SumIndices_t idx);

    // @short an enum for the final quantities displayed on hexplots
    enum SummaryIndices_t { CMAVG=0, PEDESTAL, NOISE, DELTAPEDESTAL, TOAAVG, TOTAVG, LASTSUMMARYINDEX };

    // @short label for SummaryIndices_t enum (ROOT format)
    std::string getLabelForSummaryIndex(SummaryIndices_t idx);

  } // namespace dqm

} // namespace hgcal

#endif
