#ifndef __helpers_h__ 
#define __helpers_h__ 

#include "ROOT/RVec.hxx"

using namespace ROOT::VecOps; 

using rvec_f = const RVec<float>;
using rvec_i = const RVec<int>;
using rvec_b = const RVec<bool>;


/**
    @short assigns the CM indices to use for each channel based on a match between the module and erx numbers
*/
rvec_f assignAveragedCM(const rvec_i &ch_module, const rvec_i &ch_erx,const rvec_i &cm_module, const rvec_i &cm_erx, const rvec_i &cm) {
    
  std::vector<float> avgcm(ch_erx.size(),0.);

  for(size_t i=0; i<ch_erx.size(); i++){
    auto mask = (cm_erx == ch_erx[i]) && (cm_module==ch_module[i]);
    //assert( Sum(mask)==2 );
    avgcm[i] = Mean( cm[mask] );
  }
  
  return rvec_f(avgcm.begin(),avgcm.end());
}

/**
   @short selects the neighouring cells around a seed with a delta (u,v) radius
 */
rvec_b channelNeighbors(const rvec_i &HGC_module,const rvec_i &HGC_ch,const rvec_i &HGC_u,const rvec_i &HGC_v, int econd, int seed_u, int seed_v,int maxduv=1) {

  std::vector<bool> mask(HGC_module.size(),false);

  for(size_t i=0; i<HGC_module.size(); i++){

    if(HGC_module[i]!=econd) continue;

    int du=HGC_u[i]-seed_u;
    if(du>maxduv || du<-maxduv) continue;

    int dv=HGC_v[i]-seed_v;
    if(dv>maxduv || dv<-maxduv) continue;

    if(dv>du+maxduv || dv<du-maxduv) continue;
    
    mask[i]=true;
  }
  return rvec_b(mask.begin(),mask.end());
}

/**
   simple matcher in u,v coordinates
 */
rvec_b matchesUV(const rvec_i &HGC_u,const rvec_i &HGC_v,int seed_u, int seed_v) {
  return (HGC_u==seed_u) && (HGC_v==seed_v);  
}


#endif
