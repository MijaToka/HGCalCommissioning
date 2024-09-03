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
rvec_b channelNeighbors(const rvec_i &HGCDigi_module,const rvec_i &HGCDigi_ch,const rvec_i &HGCDigi_u,const rvec_i &HGCDigi_v, int econd, int seed_u, int seed_v,int maxduv=1) {

  std::vector<bool> mask(HGCDigi_module.size(),false);

  for(size_t i=0; i<HGCDigi_module.size(); i++){

    if(HGCDigi_module[i]!=econd) continue;

    int du=HGCDigi_u[i]-seed_u;
    if(du>maxduv || du<-maxduv) continue;

    int dv=HGCDigi_v[i]-seed_v;
    if(dv>maxduv || dv<-maxduv) continue;

    if(dv>du+maxduv || dv<du-maxduv) continue;
    
    mask[i]=true;
  }
  return rvec_b(mask.begin(),mask.end());
}

/**
   @short simple matcher in u,v coordinates
 */
rvec_b matchesUV(const rvec_i &HGCDigi_u,const rvec_i &HGCDigi_v,int seed_u, int seed_v) {
  return (HGCDigi_u==seed_u) && (HGCDigi_v==seed_v);  
}

/**
   @short coherent noise estimator
   computes either the direct sum or the alternated sum over the channels a ROC
   for the purpose of estimating the coheerent noise
   mode = 0 : return roc indices
          1 : return # channels
          2 : direct sum
          3 : alternated sum
 */
rvec_f sumOverRoc(const rvec_i &ch, const rvec_f &en, int mode) {

  std::vector<float> sums;

  //loop over channels and build sums per roc
  for(size_t i=0; i<ch.size(); i++){
    
    int iroc = int(ch[i]/74);
    if(int(sums.size())<=iroc) sums.resize(iroc+1,0.);

    if(mode==0) {
      sums[iroc]=iroc;
    }
    else if (mode==1) {
      sums[iroc]+=1;
    }
    else {
      float kfact =
        mode==3 ?
        (ch[i]%2==0 ? -1 : 1) :
        1.;
      sums[iroc] += en[i]*kfact;
    }
  }


  return rvec_f(sums.begin(), sums.end());
}


#endif
