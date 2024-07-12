#include "HGCalCommissioning/DQM/interface/HGCalSysValDQMCommon.h"

namespace hgcal
{
      namespace dqm {
            
            //
            std::string getLabelForSumIndex(SumIndices_t idx) {
                  std::string label = "N(CM)";
                  if(idx==hgcal::dqm::SumIndices_t::SUMCM) label = "#sum CM";
                  else if(idx==SumIndices_t::NADC) label = "N(ADC)";
                  else if(idx==SumIndices_t::SUMADC) label = "#sum ADC";
                  else if(idx==SumIndices_t::SUMADC2) label = "#sum ADC^{2}";
                  else if(idx==SumIndices_t::NADCM1) label = "N(ADC_{-1})";
                  else if(idx==SumIndices_t::SUMADCM1) label = "#sum ADC_{-1}";
                  else if(idx==SumIndices_t::DELTAADC) label = "#Delta ADC";
                  else if(idx==SumIndices_t::NTOA) label = "N(TOA)";
                  else if(idx==SumIndices_t::SUMTOA) label = "#sum TOA";
                  else if(idx==SumIndices_t::NTOT) label = "N(TOT)";
                  else if(idx==SumIndices_t::SUMTOT) label = "#sum TOT";
                  return label;
            }

            //
            std::string getLabelForSummaryIndex(SummaryIndices_t idx) {
                  std::string label = "<CM>";
                  if(idx==SummaryIndices_t::PEDESTAL) label = "Pedestal";
                  else if(idx==SummaryIndices_t::NOISE) label = "Noise";
                  else if(idx==SummaryIndices_t::DELTAPEDESTAL) label = "#DeltaPedestal";
                  else if(idx==SummaryIndices_t::TOAAVG) label = "<TOA>";
                  else if(idx==SummaryIndices_t::TOTAVG) label = "<TOT>";
                  return label;
            }

      } // namespace dqm
      
} // namespace hgcal