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

def revive_hex(str_json):
    str_json = re.sub(r'"headerMarker":\s+([0-9])', r'"headerMarker": 0x\1', str_json)
    return str_json
    
def index_gain(gain):
    mapping = { 260 : 1, 293 : 2, 572 : 4 };
    # 260 = 0100000100: [0100](Cf: 4) - [00](Cf_comp: 0) - [0100](Rf: 4) => 80 Cf
    # 293 = 0100100101: [0100](Cf: 4) - [10](Cf_comp: 2) - [0101](Rf: 5) => 160 Cf
    # 572 = 1000111100: [1000](Cf: 8) - [11](Cf_comp: 3) - [1100](Rf: 12) => 320 Cf
    if gain not in mapping:
        print(f"error: gain %d not found" % gain)
        return -1
    return mapping[gain]
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', required=True, help='config yaml')
    parser.add_argument('--run', required=True, help='run scan yaml')
    parser.add_argument('--out', help='output json')
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
            gain = int(t_gain, 2)
            gain = index_gain(gain)
            Gain.append(gain)

        i_DigitalHalf = data_conf[f"roc_s%d"%i]["sc"]["DigitalHalf"]
        for jd in i_DigitalHalf.values():
            CalibrationSC.append(jd["CalibrationSC"])

    characMode = data_run["metaData"]["characMode"]

    result = {}
    result["ML-F3PT-TX-0003"] = { "headerMarker": 154, "Gain": Gain, "characMode" : characMode, "CalibrationSC" : CalibrationSC }
    result["ML-F3PC-MX-0003"] = { "headerMarker": 154, "Gain": Gain, "characMode" : characMode, "CalibrationSC" : CalibrationSC }

    str_result = pprint(result)
    str_result = revive_hex(str_result)

    print(str_result)

    if file_out:
        with open(file_out, 'w') as f:            
            print(str_result, file=f)

