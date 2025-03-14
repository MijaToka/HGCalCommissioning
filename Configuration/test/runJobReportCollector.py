import sys
import os
import argparse
import glob
import json
import pprint
import pandas as pd # type: ignore

def collectJobReportData(input : str) -> pd.DataFrame:
    """build a flat report from individual job reports"""
	
    metrics=['AvgEventTime','EventThroughput','MaxEventTime','MinEventTime','NumberEvents','TotalJobCPU','TotalJobTime']
    def _getJobData(f : str) -> list:
        fin = open(f,'r')
        job = json.load(fin)
        InputDir = os.path.dirname(job['input'][0])
        Run = job['run']
        RecoEra = job['era']
        if not 'JobReport' in job : return []

        jobreport = job['JobReport']
        data=[]
        for i,step in enumerate(jobreport['Step']):
            data.append(
                [Run, step, RecoEra, InputDir] + [jobreport[m][i] for m in metrics if m!='Step']
            )
        return data
    
    #collect data for all reports
    data=[]
    flist = [f for f in glob.glob(f'{input}/*.json')]
    for f in flist:
        try:
            data += _getJobData(f)
        except Exception as e:
            pass

	#convert to dataframe
    columns = ['Run','Step','RecoEra','InputDir'] + metrics
    df = pd.DataFrame(data, columns=columns)
    df = df.astype( dict([(m,float) for m in metrics]) )
    return df


def convertToRunReport(data : pd.DataFrame) -> dict:
    
    """groups by step and aggregates metrics"""
    
    report = data.groupby(['Step']).agg(
	EventThroughput=('EventThroughput', 'mean'),
	MaxEventTime=('MaxEventTime', 'max'),		
	AvgEventTime=('AvgEventTime', 'mean'),
	MinEventTime=('MinEventTime', 'min'),
	NumberEvents=('NumberEvents', 'sum'),
	TotalJobCPU=('TotalJobCPU', 'sum'),
	TotalJobTime=('TotalJobTime', 'sum'),
	LumiSections=('TotalJobTime', 'count'),		
    )
    report.reset_index(inplace=True)
    report_dict = {
	'Report':dict([
	    (c,report[c].values.tolist()) for c in report.columns if not c in ['LumiSections']
	])
    }
    report_dict['Report'].update( {
        'InputDir':data['InputDir'].iloc[0],
        'LumiSections':int(report['LumiSections'].iloc[0]),
        'Era':data['RecoEra'].iloc[0],	
    } )
    return report_dict

def buildRunReport(input : str) -> dict:
	data = collectJobReportData(input)
	report = convertToRunReport(data)
	return report

def main():
        
	parser = argparse.ArgumentParser(prog='runReportBuilder',
					 description='makes an overall summary of the jobReport json files',
                                         epilog='Developed for HGCAL system tests')
	parser.add_argument('-i', '--input', default=None, help='base directory where to find the reports (default: %(default)s)', type=str)
	parser.add_argument('-o', '--output', default='run_report.json', help='output filename (default: %(default)s)', type=str)
	args = parser.parse_args()

	report = buildRunReport(args.input)
	with open(args.output,'w') as fout:
		fout.write( json.dumps(report, ensure_ascii=True, indent=4) )

	sys.exit(os.EX_OK)

if __name__ == '__main__':
        main()
