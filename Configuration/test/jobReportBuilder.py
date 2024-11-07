import sys
import os
import re
import argparse
import json
import pprint
import glob

def processFwkReports(basedir : str,
                      fwkreportsPatt : str = 'FrameworkJobReport_(.*).xml',
                      metrics : list = ['NumberEvents','AvgEventTime','MaxEventTime','MinEventTime','EventThroughput','TotalJobCPU','TotalJobTime']):

    """parse the required information from the xml file. 
    AS ElementTree seems to fail processing these xml files a simple regex is used"""
    
    #wraps the parsing of metrics from the framework job report
    def _parseMetrics(f,metrics): 
        data={}
        with open(f, 'r') as inf:
            xmlstr = inf.read().replace('\n', '')
            for m in metrics:
                rgx = f'<Metric Name="{m}" Value="(\\d+(?:\\.\\d+)?)"/>'
                result = re.findall(rgx, xmlstr)
                if len(result)==0:
                    data[m]="0"
                else:
                    data[m] = re.findall(rgx, xmlstr)[0]
        return data

    #find FWK job reports in the directory given and parse them
    #the reconstruction step is identified based on the regex pattern
    report=dict([(k,[]) for k in ['Step']+metrics])
    for f in [ os.path.join(basedir,xml) for xml in os.listdir(basedir) if re.search(fwkreportsPatt,xml) ]:        
        try:
            step = re.findall(fwkreportsPatt,f)[0]
        except:
            continue
        report['Step'].append(step)
        step_data = _parseMetrics(f,metrics)
        for k,v in step_data.items():
            report[k].append(v)
    return {"JobReport":report}


def main():

    #command line arguments
    parser = argparse.ArgumentParser(prog='jobReportBuilder',
                                     description='parses the framework job reports and collates information with the initial job json if available',
                                     epilog='Developed for HGCAL system tests')
    parser.add_argument('-i', '--input', default=None, help='jobs output directory (default: %(default)s)', type=str, required=True)
    parser.add_argument('-j', '--json',  default=None, help='json file used to seed a reco job (built by RunRegistry) (default: %(default)s)', type=str)
    parser.add_argument('--fwkreportsPatt', default='FrameworkJobReport_(.*).xml', 
                        help='regex pattern used to extract the step the framework job report refers to (default: %(default)s)', type=str)
    parser.add_argument('-o', '--output', default='job_report.json',
                        help='output filename (default: %(default)s)', type=str)
    args = parser.parse_args()

 
    #check inptu directory
    if os.path.isdir(args.input):
        basedir=args.input
    else:
        raise ValueError('Invalid json or directory : {args.input}')
    
    #start report (using json if available)
    data={}
    if not args.json is None and os.path.isfile(args.json):
        with open(args.json,'r') as fin:
            data.update( json.load(fin) )
       
    #update report with FWK job reports  
    data.update(
        processFwkReports(basedir, fwkreportsPatt=args.fwkreportsPatt)
    )

    #save final report
    with open(args.output, 'w', encoding='utf-8') as fout:
        json.dump(data, fout, ensure_ascii=True, indent=4)
    print(f'Report stored in {args.output}')

    sys.exit(os.EX_OK)


if __name__ == '__main__':
    main()
