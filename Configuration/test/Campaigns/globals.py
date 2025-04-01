import json
import os
import re

def defineGlobals(workflow):

    """defines global variables which can be used to define the configuration of the rules"""
    
    cfgurl = workflow.config_settings.configfiles[0]
    
    with open(cfgurl,'r') as cfg:
        job_dict = json.load(cfg)

    #convert the job dict to a common parameter set that can be used by the rules
    common_params = {}
    if "run" in job_dict:
        common_params["run"] = str(job_dict["run"])
    if "lumisection" in job_dict:
        common_params["lumi"] = str(job_dict["lumisection"])
    if "era" in job_dict: 
        common_params["era"] = str(job_dict["era"])
    if "input" in job_dict and type(job_dict["input"])==list:
        common_params["inputFiles"] = ','.join(job_dict["input"][1:])
        common_params["inputTrigFiles"] = ','.join( [job_dict["input"][0],] )
    if "yaml" in job_dict:
        common_params["yamls"] = f'\"{job_dict["yaml"]}\"'
    common_params["maxEvents"] = str(job_dict['maxevents']) if 'maxevents' in job_dict else "-1"
    
    return cfgurl, job_dict, common_params
