#! /usr/bin/env python3
# Author: Izaak Neutelings (March 2024)
# Description: JSON encoder to keep JSONs compact & readable 
# Sources:
#   https://stackoverflow.com/questions/16264515/json-dumps-custom-formatting

import json
import numpy as np
  
class CompactJSONEncoder(json.JSONEncoder):

  """ A JSON Encoder that puts small lists on single lines. """
  
  def __init__(self, *args, **kwargs):
    #kwargs.setdefault("indent",2)
    super().__init__(*args, **kwargs)
    self.indentation_level = 0
  
  def encode(self, o):
    """Encode JSON object *o* with respect to single line lists."""
    if isinstance(o, (list, tuple)):
      if self._is_single_line_list(o):
        return "[ " + ", ".join(json.dumps(el) for el in o) + " ]"
      else:
        self.indentation_level += 1
        output = [self.indent_str + self.encode(el) for el in o]
        self.indentation_level -= 1
        return "[\n" + ",\n".join(output) + "\n" + self.indent_str + "]"
    elif isinstance(o, dict):
      self.indentation_level += 1
      output = [self.indent_str + f"{json.dumps(k)}: {self.encode(v)}" for k, v in o.items()]
      self.indentation_level -= 1
      return "{\n" + ",\n".join(output) + "\n" + self.indent_str + "}"
    else:
      return json.dumps(o)
  
  def _is_single_line_list(self, o):
    #print(type(o),len(o),len(str(o)))
    if isinstance(o, (list, tuple)):
      return not any(isinstance(el, (list, tuple, dict)) for el in o)\
         and len(o)>=2 #and len(str(o))-2<=60
  
  @property
  def indent_str(self) -> str:
    return " " * self.indentation_level * self.indent
  
  def iterencode(self, o, **kwargs):
    """Required to also work with `json.dump`."""
    return self.encode(o)

def saveAsJson(url : str, results : dict, compress=False):
    """takes care of saving to a json file"""
    
    if compress:
        json_str = json.dumps(results,cls=CompactJSONEncoder) + "\n"
        json_bytes = json_str.encode('utf-8')
        with gzip.open(url, 'w') as outfile:
            outfile.write(json_bytes)
    else:
        with open(url,'w') as outfile:
            json.dump(results,outfile,cls=CompactJSONEncoder,sort_keys=True,indent=2)
