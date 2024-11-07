import numpy as np
import pandas as pd
from scipy.odr import ODR, Model, Data, RealData
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.backends.backend_pdf
import mplhep as hep
from typing import List

class CalPulseModel:
    """
    receives a dataframe with several channels and gains and tries to fit a CalPulse model to each
    the plots and fit results will be stored if the fit_out string is passed
    """

    def __init__(self, df, fit_out : str =  '', minq_totfit : float = 280.):

        self.minq_totfit = minq_totfit
        
        #start the backend pdf if required
        self.pdf = matplotlib.backends.backend_pdf.PdfPages(fit_out+'.pdf') if len(fit_out)>0 else None
        
        #run the fits and store in pandas
        fit_results=[]
        for (ch,gain), group in df.groupby(['channel','gain']):
            try:
                fit_title = f'Channel:{ch:d} Gain:{int(gain):d}'
                fit_results.append(
                    [ch,gain]+
                    self.fitCalPulseModelToChannel(group, gain=gain, fit_title=fit_title)
                )
            except Exception as e:
                print(f'Skipping Channel={ch} for gain {gain} : {e}')
                failed_result=[ch,gain]+[None]*16
                fit_results.append( failed_result )    

        self.fit_results = pd.DataFrame(fit_results,columns=['channel','gain',
                                                             'adc2fC','adc0','tot2fC','tot0','totlin','a',
                                                             'adc2fC_unc','adc0_unc',
                                                             'tot2fC_unc','tot0_unc','totlin_unc','a_unc',
                                                             'adc_chi2','adc_dof', 'tot_chi2','tot_dof'])
        self.fit_results['erx'] = self.fit_results['channel']/37
        self.fit_results = self.fit_results.astype({'erx': 'int32'})
        
        #save results if required
        if  len(fit_out)>0:            
            self.fit_results.to_feather(fit_out+'.feather')
            self.pdf.close()


    def fitCalPulseModelToChannel(self, data, 
                                  gain : int = 0,
                                  mincounts : int = 0,
                                  maxadc : int = 800, 
                                  totlin : int = 180,
                                  fit_title : str = 'A great CalPulse fit') :        
        """receives the channel data (data frame with columns =[gain, isadc, inj_q]
            and steers the charge linearity fit
            Returns the best fit parameters, the diagonal of the covariance matrix, 
            the chi2 and the degrees of freedom"""
        

        mask_base = (data['gain']==gain) & (data['counts']>mincounts)
        mask_adc = (data['isadc']==True) & (data['counts']<maxadc) & mask_base
        mask_tot = (data['isadc']==0) & mask_base & (data['counts_spread']>1)
        mask_tot_lin = mask_tot & (data['counts']>totlin) & (data['counts_spread']>1)

        #
        #ADC fit
        #
        counts_adc = data[mask_adc]['counts'].values
        counts_adc_unc = 0.5*data[mask_adc]['counts_spread'].values
        q_adc = data[mask_adc]['inj_q'].values        
        q_per_adc = counts_adc / q_adc
        q_per_adc_qtl  = np.percentile(q_per_adc[q_adc<160], [16,84])
        mask_adc_fit = (q_per_adc>  q_per_adc_qtl[0]) & (q_per_adc < q_per_adc_qtl[1])
        fit_data = RealData(counts_adc[mask_adc_fit], q_adc[mask_adc_fit], sx=counts_adc_unc[mask_adc_fit])
        model = Model(self.chinj_linmodel)
        odr = ODR(fit_data, model, beta0=[5.,150.])
        odr.set_job(fit_type=2) #ordinary least square
        output = odr.run()
        popt_adc = output.beta
        sd_adc = output.sd_beta
        dof_adc = counts_adc.shape[0]-2
        chi2_adc = output.sum_square
        qpred_adc = self.chinj_linmodel(popt_adc,counts_adc)

        #
        #TOT fit
        #
        #linear part (estimate first in order not be too biased by the non-linear part)
        counts_tot_lin = data[mask_tot_lin]['counts'].values
        counts_tot_lin_unc = 0.5*data[mask_tot_lin]['counts_spread'].values
        q_tot_lin = data[mask_tot_lin]['inj_q'].values
        fit_data = RealData(counts_tot_lin, q_tot_lin, sx=counts_tot_lin_unc)
        model = Model(self.chinj_linmodel)
        odr = ODR(fit_data, model, beta0 = [10.,0.])
        odr.set_job(fit_type=2)
        output = odr.run()
        popt_tot_lin = output.beta

        #stitch with non-linear part
        counts_tot = data[mask_tot]['counts'].values
        counts_tot_unc = 0.5*data[mask_tot]['counts_spread'].values
        q_tot = data[mask_tot]['inj_q'].values
        mask_tot_fit = (q_tot>self.minq_totfit)
        fit_data = RealData(counts_tot[mask_tot_fit], q_tot[mask_tot_fit], sx=counts_tot_unc[mask_tot_fit])
        model = Model(self.chinj_nonlinmodel)
        beta0 = popt_tot_lin.tolist() + [totlin,0.]
        odr = ODR(fit_data, model, beta0 = beta0)
        odr.set_job(fit_type=2)
        output = odr.run()
        popt_tot = output.beta
        sd_tot = output.sd_beta
        dof_tot = counts_tot.shape[0]-2
        chi2_tot = output.sum_square
        qpred_tot = self.chinj_nonlinmodel(popt_tot,counts_tot)
        
        infolist = [
            [
                fit_title,
                rf'$\chi^2$/dof = {chi2_adc:3.0f} / {dof_adc:d}',
                f'k = {popt_adc[0]:3.3f} counts/fC',
                rf'p = {popt_adc[1]:3.0f}'
            ],
            [
                rf'$\chi^2/dof$ = {chi2_tot:3.0f} / {dof_tot:d}',
                f'k = {popt_tot[0]:3.3f} counts/fC',
                f'p = {popt_tot[1]:3.0f}',
                f'a = {popt_tot[2]:3.0f}',
                rf'$x_{{0}}$ = {popt_tot[3]:e}'
            ]
        ]
        self.showFitResults(
            [counts_adc, counts_tot],
            [q_adc, q_tot],
            [counts_adc_unc, counts_tot_unc],
            [qpred_adc, qpred_tot],
            infolist
        )

        #return results
        return popt_adc.tolist()+popt_tot.tolist()+sd_adc.tolist()+sd_tot.tolist()+[chi2_adc,dof_adc,chi2_tot,dof_tot]
    
    @staticmethod
    def chinj_linmodel(beta, x):
        """a linear charge injection model
        beta - fitting parameters (counts to charge conversion factor, pedestal for counts)
        x - counts
        """
        k,p = beta
        return k*(x-p)

    
    @staticmethod
    def chinj_nonlinmodel(beta, x):
        """a simple, non-linear charge injection model where c0 marks the transition to the linear regime
        beta - fitting parameters )counts to charge conversion factor, pedestal for counts, counts at which the junction should be imposed, coefficient of the second order polynomial)
        x - counts
        """

        k, p, x0 ,a = beta
        
        #linear branch
        clin = CalPulseModel.chinj_linmodel([k,p],x)
        
        #non-linear branch
        b = k - 2*a*x0
        c = a*(x0**2) - k*p
        cnonlin = a*x*x + b*x + c

        return np.where( x<x0, cnonlin, clin )
        
    

    def showFitResults(self, xlist :list, ylist : list, yunclist : list, ypredlist : list, infolist : list):

        if self.pdf is None: return
        
        plt.style.use([hep.style.CMS, hep.style.firamath])

        fig = plt.figure(figsize=(12,8))        
        gs = GridSpec(2, 2, width_ratios=[1, 1], height_ratios=[4, 1])
        ax = [fig.add_subplot(gs[i]) for i in range(2)]
        axr = [fig.add_subplot(gs[i+2],sharex=ax[i]) for i in range(2)]
        plt.subplots_adjust(hspace=0)
        
        ebar_style={'marker':'o','elinewidth':1,'capsize':1,'color':'k','ls':'none'}
        for i in range(2):
            idxsort = np.argsort(xlist[i])
            ax[i].plot( xlist[i][idxsort], ypredlist[i][idxsort], ls='-', c='blue' )
            ax[i].errorbar( xlist[i], ylist[i], xerr=yunclist[i], **ebar_style )
            ax[i].grid()
            ax[i].set_xlabel('{} counts'.format('ADC' if i==0 else 'TOT'))
            ax[i].set_ylabel('Injected charge [fC]')

            kwargs={'transform':ax[i].transAxes,'fontsize':13}
            for j,v in enumerate(infolist[i]):
                ax[i].text(0.06,0.90-j*0.05,v,**kwargs)
                
            ratio = ypredlist[i]/ylist[i]
            ratio_unc = yunclist[i]/ylist[i]            
            axr[i].errorbar( xlist[i], ratio, yerr=ratio_unc[i], **ebar_style)
            axr[i].set_xlabel('{} counts'.format('ADC' if i==0 else 'TOT'))            
            axr[i].set_ylim(0.72,1.28)
            axr[i].grid()
            axr[i].set_ylabel('Ratio')
            
        fig.tight_layout()
        self.pdf.savefig(fig, bbox_inches='tight') 
