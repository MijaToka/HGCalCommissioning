import sys
import os
import re
import argparse
import json
import pprint

def processFwkReports(fwkreportslist,
                      fwkreportsPatt='FrameworkJobReport_(.*).xml',
                      metrics=['NumberEvents','AvgEventTime','MaxEventTime','MinEventTime','EventThroughput','TotalJobCPU','TotalJobTime']):

    """parse the required information from the xml file. 
    AS ElementTree seems to fail processing these xml files a simple regex is used"""
    
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

    report=dict([(k,[]) for k in ['Step']+metrics])
    for f in fwkreportslist:
        step = re.findall(fwkreportsPatt,f)[0]
        report['Step'].append(step)

        step_data = _parseMetrics(f,metrics)
        for k,v in step_data.items():
            report[k].append(v)
    return {"JobReport":report}

def main():
    parser = argparse.ArgumentParser(prog='jobReportBuilder',
                                     description='parses the framework job reports and collates information with the initial job json if available',
                                     epilog='Developed for HGCAL system tests')
    parser.add_argument('--initialcfg', default=None, help='json file used to seed a reco job (built by RunRegistry) (default: %(default)s)', type=str)
    parser.add_argument('--fwkreports', default='', help='csv list of FrameworJobReports (default: %(default)s)', type=str)
    parser.add_argument('--fwkreportsPatt', default='FrameworkJobReport_(.*).xml', 
                        help='regex pattern used to extract the step the framework job report refers to (default: %(default)s)', type=str)
    parser.add_argument('-o', '--output', default='job_report.json', help='output filename (default: %(default)s)', type=str)

    args = parser.parse_args()

    data={}
    if not args.initialcfg is None and os.path.isfile(args.initialcfg):
        with open(args.initialcfg,'r') as fin:
            data.update( json.load(fin) )

    fwkreportslist=[report for report in args.fwkreports.split(',') if os.path.isfile(report)]
    data.update(
        processFwkReports(fwkreportslist,args.fwkreportsPatt)
    )

    with open(args.output, 'w', encoding='utf-8') as fout:
        json.dump(data, fout, ensure_ascii=True, indent=4)
    print(f'Report stored in {args.output}')

    sys.exit(os.EX_OK)

if __name__ == '__main__':
    main()