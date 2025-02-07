# Author: Izaak Neutelings (January 2025)
# Sources:
#    https://twiki.cern.ch/twiki/bin/viewauth/CMS/FastTimerService
#    HLTrigger/Timer/plugins/FastTimerService.cc
import os
import FWCore.ParameterSet.Config as cms


def addFastTimerService(process,logtag=''):
  """Add FastTimerService to process."""
  # https://twiki.cern.ch/twiki/bin/viewauth/CMS/FastTimerService
  # HLTrigger/Timer/plugins/FastTimerService.cc
  # upload to https://cmssdt.cern.ch/circles/web/piechart.php?local=true&resource=time_thread&colours=default&groups=packages&data_name=profiling&show_labels=true&threshold=0
  process.load("HLTrigger.Timer.FastTimerService_cfi")
  process.FastTimerService.jsonFileName = f"resources{logtag}.json"
  process.FastTimerService.writeJSONSummary = cms.untracked.bool(True)
  return process.FastTimerService
  

def addThroughoutService(process,options,logtag='',evtRes=100,maxEvts=55000,dqm=True):
  """Add ThroughputService to process."""
  # https://twiki.cern.ch/twiki/bin/viewauth/CMS/ThroughputService
  # HLTrigger/Timer/plugins/ThroughputService.cc
  if options.maxEvents>=1: #maxEvts<=0 and
      maxEvts = options.maxEvents
  process.ThroughputService = cms.Service('ThroughputService',
      eventRange = cms.untracked.uint32(maxEvts), # total number of processed events (for memory optimization)
      eventResolution = cms.untracked.uint32(evtRes), # number of events to skip (avoid initialization bias)
      printEventSummary = cms.untracked.bool(True),
      enableDQM = cms.untracked.bool(dqm),
      dqmPathByProcesses = cms.untracked.bool(False),
      dqmPath = cms.untracked.string('Throughput'),
      timeRange = cms.untracked.double(1000),
      timeResolution = cms.untracked.double(1),
  )
  process.MessageLogger.cerr.ThroughputService = cms.untracked.PSet(
      limit = cms.untracked.int32(1000000)
  )
  # output log file with comma-separated nevts vs. wallclock timestamps
  process.MessageLogger.files.ThroughputService = cms.untracked.PSet(
      filename  = cms.untracked.string(f"ThroughputService{logtag}.log"),
      threshold = cms.untracked.string('INFO'),
      default = cms.untracked.PSet(limit=cms.untracked.int32(0)),
      FwkReport = cms.untracked.PSet(
        limit = cms.untracked.int32(-1),
        reportEvery = cms.untracked.int32(10000),
      ),
      ThroughputService = cms.untracked.PSet(limit=cms.untracked.int32(1000000)),
  )
  return process.ThroughputService
  

def scaleFEDs(process,inputFiles,eraConfig,scale=1,verb=0):
  """Help function scale up input by reuing FEDs. If scale<=1: no scaling.
  Overload module locator & FED config JSON."""
  if verb>=1:
    print(f">>> scaleFEDs: Before scaling:")
    print(f">>>   eraConfig['fedId']={eraConfig['fedId']}, len(inputFiles)={len(inputFiles or [ ])}")
    print(f">>>   process.hgCalMappingESProducer.modules       ={process.hgCalMappingESProducer.modules}")
    print(f">>>   process.hgCalMappingModuleESProducer.filename={process.hgCalMappingModuleESProducer.filename}")
    print(f">>>   process.hgcalConfigESProducer.fedjson        ={process.hgcalConfigESProducer.fedjson}")
  if scale>=2:
    inputFiles = scaleFiles(inputFiles,eraConfig,scale=scale,verb=verb)
    newmodmap = f"modloc_scale{scale}.txt"
    newjson   = f"fedconfig_scale{scale}.json"
    scaleModMap(process.hgCalMappingESProducer.modules,newmodmap=newmodmap,scale=scale)
    scaleFEDConfig(process.hgcalConfigESProducer.fedjson,newjson=newjson,scale=scale)
    process.hgCalMappingModuleESProducer.filename = cms.FileInPath(newmodmap)
    process.hgCalMappingESProducer.modules        = cms.FileInPath(newmodmap)
    process.hgcalConfigESProducer.fedjson         = cms.string(newjson)
  if scale>=10:
    print(">>> Limiting number of messages from Indexer & Config producers...")
    #process.MessageLogger.suppressInfo = cms.untracked.vstring( # does not work ?
    #  'HGCalConfigurationESProducer','HGCalMappingModuleIndexer'
    #)
    process.MessageLogger.cerr.HGCalMappingModuleIndexer = cms.untracked.PSet(limit=cms.untracked.int32(6))
    process.MessageLogger.cerr.HGCalConfigurationESProducer = cms.untracked.PSet(limit=cms.untracked.int32(6))
  if verb>=1:
    print(f">>> scaleFEDs: After scaling by {scale}:")
    print(f">>>   eraConfig['fedId']={eraConfig['fedId']}, len(inputFiles)={len(inputFiles or [ ])}")
    print(f">>>   process.hgCalMappingESProducer.modules       ={process.hgCalMappingESProducer.modules}")
    print(f">>>   process.hgCalMappingModuleESProducer.filename={process.hgCalMappingModuleESProducer.filename}")
    print(f">>>   process.hgcalConfigESProducer.fedjson        ={process.hgcalConfigESProducer.fedjson}")
  return inputFiles
  

def scaleFiles(inputFiles,eraConfig,scale=1,verb=0):
  """Naively scale up input by reusing FEDs. If scale<=1: no scaling."""
  if scale<=1:
    if verb>=1:
      print(f">>> scaleFiles: Not scaling... scale={scale}")
  else:
    nfeds = len(eraConfig['fedId'])
    assert inputFiles is None or nfeds==len(inputFiles), "nfeds={nfeds}!={len(inputFiles)}=len(InputFiles)"
    fmax = max(eraConfig['fedId']) # last FED
    eraConfig['fedId'] = [n*(fmax+1)+f for n in range(scale) for f in eraConfig['fedId']]
    inputFiles = [[f for n in range(scale) for f in inputFiles]] if inputFiles else [[ ]]
    #eraConfig['fedId'] = [eraConfig['fedId'][0]+i for i in range(scale)]
    #inputFiles = [scale*inputFiles[0]]
    if verb>=1:
      print(f">>> scaleFiles: Scaling up FEDs by factor {scale}: eraConfig['fedId']={eraConfig['fedId']}")
  return inputFiles
  

def scaleModMap(oldmodmap,scale=1,newmodmap=None,overwrite=False):
  """Take modmap and duplicate FED blocks."""
  if not isinstance(oldmodmap,str):
    oldmodmap = oldmodmap.value() # assume cms.FileInPath
  if newmodmap is None:
    newmodmap = f"{oldmodmap.replace('.txt','')}_scale{scale}.txt"
  if not os.path.isfile(oldmodmap):
    print(f">>> scaleModMap: WARNING! oldmodmap={oldmodmap} does not exists!")
  if os.path.isfile(newmodmap):
    if overwrite:
      print(f">>> scaleModMap: WARNING! newmodmap={newmodmap} already exists! Overwriting...")
    else:
      return newmodmap
  header  = "plane u v irot typecode econdidx captureblock captureblockidx slinkidx fedid zside\n"
  assert oldmodmap!=newmodmap, f"oldmodmap={oldmodmap!r} == {newmodmap!r} = newmodmap"
  rows = [ ]
  ifed = header.strip().index('fedid') # column index of fedId
  maxfedid = -1
  with open(oldmodmap,'r') as infile: # read old modmap
    for i, line in enumerate(infile):
      if line and i==0 and not line[0].isdigit():
        header = line
        ifed = header.strip().split().index('fedid')
      else: # TODO: debug
        cells = line.strip().split()
        if len(cells)<=ifed:
          print(f">>> scaleModMap: WARNING! Too few columns: len(cells)={len(cells)} <= {ifed}=ifed ! Skipping...")
          continue
        fedid = int(cells[ifed])
        cells[ifed] = '$FEDID' # placeholder
        row   = ' '.join(c.ljust(17) if c.startswith('M') else c.rjust(2) for c in cells)
        rows.append((fedid,row))
        if fedid>maxfedid:
          maxfedid = fedid
  with open(newmodmap,'w') as outfile: # write new modmap
    outfile.write(header)
    for i in range(scale):
      for fedid, row in rows:
        newfedid = str(i*(maxfedid+1)+fedid).rjust(2)
        newrow   = row.replace('$FEDID',newfedid)+'\n'
        outfile.write(newrow)
  return newmodmap #cms.untracked.FileInPath(newmodmap)
  

def scaleFEDConfig(oldjson,scale=1,newjson=None,overwrite=False):
  """Take FED Config JSON and duplicate FED config."""
  import json
  if not isinstance(oldjson,str):
    oldjson = oldjson.value() # assume cms.FileInPath
  if newjson is None:
    newjson = f"{oldjson.replace('.json','')}_scale{scale}.json"
  if not os.path.isfile(oldjson):
    print(f">>> scaleFEDConfig: WARNING! oldjson={oldjson} does not exists!")
  if os.path.isfile(newjson):
    if overwrite:
      print(f">>> scaleFEDConfig: WARNING! newjson={newjson} already exists! Overwriting...")
    else:
      return newjson
  assert oldjson!=newjson, f"oldjson={oldjson!r} == {newjson!r} = newjson"
  with open(oldjson,'r') as infile: # read old config
    olddata = json.load(infile)
    oldfedids = [(int(f),f) for f in olddata]
    maxfedid  = max(f[0] for f in oldfedids)
  with open(newjson,'w') as outfile: # write new config
    newdata   = { }
    for i in range(scale):
      for oldfedid, oldkey in oldfedids:
        fedid = str(i*(maxfedid+1)+oldfedid)
        newdata[fedid] = olddata[oldkey] # copy data
    json.dump(newdata,outfile,indent=2)
  return newjson #cms.string(newjson)
  
