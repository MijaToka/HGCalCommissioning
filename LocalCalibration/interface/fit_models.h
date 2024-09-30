#ifndef __fitmodels_h__
#define __fitmodels_h__

#include "RooRealVar.h"
#include "RooFormulaVar.h"
#include "RooGaussian.h"
#include "RooLandau.h"
#include "RooFFTConvPdf.h"
#include "RooAddPdf.h"
#include "RooDataSet.h"
#include "RooDataHist.h"
#include "RooArgSet.h"
#include "RooWorkspace.h"
#include "RooFitResult.h"
#include "RooPlot.h"

#include "TH1.h"
#include "TF1.h"
#include "TCanvas.h"
#include "TFile.h"

#include <chrono>
#include <string>
#include <vector>
#include <iostream>

struct MIPFitResults {
  std::vector<std::string> parNames;
  std::vector<float> parVals, parUncs;
  float chi2, ndof;
  int status;
  TCanvas *fitPlot;
};

/**
   @short silence the many roofit messages
 */
void shushRooFit()
{
  using namespace RooFit;

  RooMsgService::instance().setSilentMode(true);
  RooMsgService::instance().getStream(0).removeTopic(Minimization);
  RooMsgService::instance().getStream(1).removeTopic(Minimization);
  RooMsgService::instance().getStream(1).removeTopic(ObjectHandling);
  RooMsgService::instance().getStream(1).removeTopic(DataHandling);
  RooMsgService::instance().getStream(1).removeTopic(Fitting);
  RooMsgService::instance().getStream(1).removeTopic(Plotting);
  RooMsgService::instance().getStream(0).removeTopic(InputArguments);
  RooMsgService::instance().getStream(1).removeTopic(InputArguments);
  RooMsgService::instance().getStream(0).removeTopic(Eval);
  RooMsgService::instance().getStream(1).removeTopic(Eval);
  RooMsgService::instance().getStream(1).removeTopic(Integration);
  RooMsgService::instance().getStream(1).removeTopic(NumIntegration);
  RooMsgService::instance().getStream(1).removeTopic(NumIntegration);
  RooMsgService::instance().getStream(1).removeTopic(Caching);
}

/**
   @short defines the workspace needed to fit the MIP signal
 */
RooWorkspace *defineMIPFitWorkspace(float xmin=-10,float xmax=50,
                                    float pedestalmin=-10, float pedestalmax=10,
                                    float noisemin=0.5, float noisemax=10.,
                                    float mpvlmin=5., float mpvlmax=35.,
                                    float singlemip_fracmin=0.6) {

  using namespace RooFit;

  RooRealVar x("x", "x", xmin, xmax);
 
  // noise modelled with a gaussian
  RooRealVar loc("loc", "pedestal", pedestalmin, pedestalmax);
  RooRealVar sigma("sigma", "noise", noisemin, noisemax);
  RooGaussian noise_pdf("noise_pdf", "Noise component", x, loc, sigma);
  RooRealVar loc0("loc0","pedestal0", 0.);
  RooGaussian noise0_pdf("noise_pdf", "Noise component", x, loc0, sigma);
 
  // signal pdf : landau (x) gauss
  RooRealVar mpv1("mpv", "MPV landau", mpvlmin, mpvlmax);
  RooFormulaVar mpv2("mpv2","2*@0",RooArgList(mpv1));   
  RooRealVar sigmal("sigmal", "Width landau", 1, 1, mpvlmax*2);
  RooLandau singlemip_landau("singlemip_landau", "Sungle MIP Landau PDF", x, mpv1, sigmal);
  RooLandau doublemip_landau("doublemip_landau", "Double MIP Landau PDF", x, mpv2, sigmal);
  RooFFTConvPdf singlemip_pdf("singlemip_pdf", "single mip (X) gaus", x, singlemip_landau, noise0_pdf);
  RooFFTConvPdf doublemip_pdf("doublemip_pdf", "single mip (X) gaus", x, doublemip_landau, noise0_pdf);
  
  // Sum the signal components into a composite signal pdf
  RooRealVar singlemip_frac("singlemip_frac", "fraction of single mip in signal",singlemip_fracmin,1.);
  RooAddPdf sig("sig", "Signal", RooArgList(singlemip_pdf, doublemip_pdf), singlemip_frac);
 
  // Sum the composite signal and background
  RooRealVar bkg_frac("bkg_frac", "fraction of background", 0.8, 0., 1.);
  RooAddPdf model("model", "N+S1+S2", RooArgList(noise_pdf, sig), bkg_frac);

  // Create a new empty workspace
  RooWorkspace *w = new RooWorkspace("w", "mip fit workspace");
  w->import(model);
  return w;
}

/**
   @short runs the MIP fit on a histogram and returns the result summary
 */
MIPFitResults runMIPFit(TH1 *h, RooAbsPdf *model, RooRealVar *x) {

  using namespace RooFit;
  
  //convert to RooDataHist and update variable binning and limits
  std::unique_ptr<RooDataHist> dh{new RooDataHist(h->GetName(),h->GetTitle(), *x, Import(*h))};
  x->setMin(h->GetXaxis()->GetXmin());
  x->setMax(h->GetXaxis()->GetXmax());
  int nbins = h->GetNbinsX();
  x->setBins(nbins);

  //run a chi2 fit
  RooFitResult *res= model->chi2FitTo(*dh, Save(1));

  //fill the summary
  MIPFitResults toReturn;
  toReturn.status = res->status();
  auto parsFinal = res->floatParsFinal();
  for (int i = 0; i < parsFinal.getSize(); i++) {
    RooRealVar *p = (RooRealVar *)parsFinal.at(i);
    toReturn.parNames.push_back(p->GetName());
    toReturn.parVals.push_back(p->getVal());
    toReturn.parUncs.push_back(p->getError());
  }

  //compute chi^2 (remove entries with 0)
  std::unique_ptr<RooAbsData> dsmall{dh->reduce(EventRange(1, 1000000000))};
  std::unique_ptr<RooDataHist> dhsmall{static_cast<RooDataSet&>(*dsmall).binnedClone()};
  std::unique_ptr<RooAbsReal> chi2_lowstat{model->createChi2(*dhsmall)};
  toReturn.ndof = nbins - parsFinal.getSize();
  toReturn.chi2 = chi2_lowstat->getVal();

  toReturn.fitPlot=new TCanvas("c","c",500,500);
  RooPlot *frame = x->frame();
  dh->plotOn(frame);
  model->plotOn(frame);
  model->paramOn(frame);
  frame->Draw();
  
  return toReturn;
}

//
void test_mip_fit(int nbins=200) {

  using namespace RooFit;

  shushRooFit();
  
  RooWorkspace *w = defineMIPFitWorkspace();

  auto *x = w->var("x");
  x->setBins(nbins);

  auto *model = w->pdf("model");
  std::unique_ptr<RooDataSet> d{model->generate(RooArgSet(*x), 10000)};
  auto *h = d->createHistogram("data",*x);

  auto start = std::chrono::high_resolution_clock::now();
  MIPFitResults fr = runMIPFit(h, model, x);
  auto stop = std::chrono::high_resolution_clock::now();
  std::chrono::duration<double> elapsed_seconds = stop - start;

  //report
  std::cout << "Total elapsed time during fit: " << elapsed_seconds.count() << "s" << std::endl;
  std::cout << "Fit results" << std::endl;
  std::cout << "Status: " << fr.status << " chi2/ndof: " << fr.chi2 << "/" << fr.ndof << std::endl;
  std::cout << "Fitted parameters" << std::endl;
  for(size_t i=0; i<fr.parNames.size(); i++)
    std::cout << fr.parNames[i] << ": " << fr.parVals[i] << " +/- " << fr.parUncs[i] << std::endl; 

  TFile *fOut = TFile::Open("test_mip_fit_results.root","RECREATE");
  fOut->cd();
  fr.fitPlot->Write();
  fOut->Close();
  
  h->Delete();
  w->Delete();
}

#endif
