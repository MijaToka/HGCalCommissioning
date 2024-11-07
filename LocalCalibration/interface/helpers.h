#ifndef __helpers_h__ 
#define __helpers_h__ 

#include "ROOT/RVec.hxx"

using namespace ROOT::VecOps; 

using rvec_f = const RVec<float>;
using rvec_i = const RVec<int>;
using rvec_b = const RVec<bool>;

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

/**
   @short computes the common mode noise in different flavours
   1. CM2 = (CM0+CM1)/2 in the same eRx (mode=2)
   2. CM4 = (CM0+CM1+CM2+CM3)/4 in the same ROC (mode=4)
   3. CM* =(CM0+CM1+CM2+CM3+...)/N in the same module (mode=-1)
   it is assumed that the vector of cm is already filtered within a single module
 */
rvec_f commonMode(const rvec_i &cm, int mode=2) {

  assert((mode==2 || mode==4 || mode==-1) && cm.size()%37==0);

  //
  int nErx = int(cm.size()/37);

  //build the sums to assign per eRx
  std::vector<float> cmavg(nErx,0.);
  std::vector<float> navg(nErx,0.);
  for(int i=0; i<nErx; i++) {

    cmavg[i] += cm[i*37];
    navg[i] += 2;

    //sum all eRx
    if(mode==-1) {
      for(int j=0; j<nErx; j++) {
        if(i==j) continue;
        cmavg[i] += cm[j*37];
        navg[i] += 2;
      }      
    }

    //sum in the same ROC
    if(mode==4) {      
      if(i%2==1) {
        cmavg[i] += cm[(i-1)*37];
        navg[i] += 2;
      }
      if(i%2==0 && i<nErx-1) {
        cmavg[i] += cm[(i+1)*37];
        navg[i] += 2;
      }
    }
  }//end for

  //assign the CM to use per readout channel
  std::vector<float> chcm(cm.size(),0.);
  for(size_t i=0; i<cm.size(); i++){    
    int iErx( int(i/37) );
    chcm[i] =  navg[iErx]>0 ? cmavg[iErx] / navg[iErx] : 0.;
  }

  return rvec_f(chcm.begin(), chcm.end());
}



#endif
