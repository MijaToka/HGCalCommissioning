import os
import sys
import pprint
import json
import argparse
import subprocess

def submitWrappedTasks(tasks : list, classname : str = 'HGCALCalPulse', dryRun : bool = False):

    """
    this function receives a list of tasks defined by a calibration task and puts them in a condor file to be submitted
    returns a list of condor JDL files which can be submitted for remote execution of the task
    """

    #loop over tasks and create sub-tasks
    for i,t in enumerate(tasks):

        #for each create a json with all commandline arguments but
        #updating for temporary outputs (Chunks)
        output, typecode, task_spec, cmdargs = t
        cmdargs = vars(cmdargs).copy()
        cmdargs['output'] = output + '/Chunks'
        cmdargs['task_spec'] = task_spec
        cmdargs['forceRewrite'] = True
        cmdargs['moduleList'] = [typecode]
        cmdargs['createHistoFillerTask'] = False #disable

        #write task in a json
        subtasksdir=output+'/SubTasks'
        os.makedirs(subtasksdir, exist_ok=True)
        subtasksdesc=f'{subtasksdir}/task_{i}.json'
        with open(subtasksdesc, 'w') as fout:
            json.dump(cmdargs, fout, ensure_ascii=False)

        #create a condor file further splitting the task per index
        with open(task_spec,'r') as f:
            rdf_spec = json.load(f)
        index_list = [ node["metadata"]["index"] for node in rdf_spec["samples"].values() ]
        condor = createHTCondorJDL(classname, subtasksdesc, index_list)

        #submit
        if dryRun: continue
        result = subprocess.run(['condor_submit',condor], capture_output=True, text=True)
        print('stdout: ',result.stdout)
        print('stderr: ',result.stderr)



def createHTCondorJDL(classname : str, subtaskdesc : str, index_list : list = [-1]):

    """creates a HTCondor JDL to call HGCALCalibTaskWrapper for each index in the list"""
    
    condorout = subtaskdesc.replace('.json','_condor.sub')
    jobsdir = os.path.dirname(condorout)
    calibdir = os.path.dirname( os.path.realpath(__file__) ).replace('/scripts','')
    with open(condorout,'w') as condor:
        condor.write(f"executable = scripts/runlocalhgcalcalibtask.sh\n")
        condor.write(f"calibdir = {calibdir}\n")
        condor.write(f"workflow = {classname}\n")
        condor.write(f"task_spec = {subtaskdesc}\n")
        condor.write(f"arguments = -s $(workflow).py -j $(task_spec) -i $(index) -c $(calibdir)\n")
        condor.write(f"output = {jobsdir}/$(ClusterId).out\n")
        condor.write(f"error = {jobsdir}/$(ClusterId).err\n")
        condor.write(f"log = {jobsdir}/$(ClusterId).log\n")
        condor.write('transfer_output_files   = ""\n')
        condor.write(f'+JobFlavour  = "longlunch"\n')
        #condor.write(f'+AccountingGroup = "group_u_CMST3.all"\n')
        condor.write(f'MY.WantOS = "el9"\n')
        condor.write(f'queue index from (\n')
        for i in index_list:
            condor.write(f'\t {i}\n')
        condor.write(f')')            
    return condorout


def main():

    #parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--script",
                        help='the script to run (expected inside HGCalCommissioning/LocalCalibration/scripts)=%(default)s',
			default="HGCALCalPulse.py")
    parser.add_argument("-j", "--json",
                        help='the json file describing the command line arguments to execute=%(default)s',
			default=None)
    parser.add_argument("--idx", help='index to execute locally (-1 = all)', default=-1, type=int)
    args = parser.parse_args()
    
    #rebuild the arguments from the input json
    args_list = ''
    with open(args.json, 'r') as f:
        args_dict = json.load(f)
    args_dict['moduleList'] = ','.join(args_dict['moduleList'])
    args_dict['relays'] = ' '.join([f'{r:d}' for r in args_dict['relays']])
    if args.idx>=0:
        args_dict['task_spec'] = f"{args_dict['task_spec']}:{args.idx}"
    for k, v in args_dict.items():
        if type(v) is None : continue
        if type(v)==bool:
            if not v: continue
            args_list += f'--{k} '
        elif type(v)==str and len(v)==0:
            continue
        else:
            args_list += f'--{k} {v} '

    #execute the script
    #os.system(f'python3 scripts/{args.script} {args_list}')
    result = subprocess.run(['python3', f'scripts/{args.script}'] + args_list.split(),
                            capture_output=True,
                            text=True)
    print(result.stdout)
    print(result.stderr)
    
if __name__ == '__main__':
    main()    
