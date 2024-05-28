import yaml
import json
import argparse
import re

def pprint(d):
    # print(json.dumps(d, indent=2))
    def repl_func(match: re.Match):
        return " ".join(match.group().split())
    str_json = json.dumps(d, indent=2)
    str_json = re.sub(r"(?<=\[)[^\[\]]+(?=])", repl_func, str_json)
    return str_json

    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', required=True, help='config yaml')
    parser.add_argument('--run', required=True, help='run scan yaml')
    parser.add_argument('--out', required=True, help='output json')
    args = parser.parse_args()
    file_conf = args.conf
    file_run = args.run
    file_out = args.out

    data_conf = {}
    with open(file_conf, 'r') as f:
        data_conf = yaml.load(f, Loader=yaml.SafeLoader)
    
    data_run = {}
    with open(file_run, 'r') as f:
        data_run = yaml.load(f, Loader=yaml.SafeLoader)

    Gain = []
    CalibrationSC = []
    for i in range(3):
        i_GlobalAnalog = data_conf[f"roc_s%d"%i]["sc"]["GlobalAnalog"]
        for jg in i_GlobalAnalog.values():
            # print(f'{jg["Cf"]}{jg["Cf_comp"]}{jg["Rf"]}')
            t_gain = f'{jg["Cf"]:04b}{jg["Cf_comp"]:02b}{jg["Rf"]:04b}'
            # print(t_gain)
            gain = int(t_gain, 2)
            Gain.append(gain)

        i_DigitalHalf = data_conf[f"roc_s%d"%i]["sc"]["DigitalHalf"]
        for jd in i_DigitalHalf.values():
            CalibrationSC.append(jd["CalibrationSC"])

    characMode = data_run["metaData"]["characMode"]

    result = {}
    result["ML-XXXX-YY-NNNN"] = { "Gain": Gain, "characMode" : characMode, "CalibrationSC" : CalibrationSC }

    str_result = pprint(result)
    
    with open(file_out, 'w') as f:
        print(str_result, file=f)

