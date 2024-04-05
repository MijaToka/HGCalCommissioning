import FWCore.ParameterSet.Config as cms

def diphotonEEBias(process):
    return defineEndcapBasedBias(process,"genParticles",'pt>10 && abs(pdgId)==22 && status==1',2)

def defineEndcapBasedBias(process,
                          coll="genParticles",
                          basecuts='pt>10 && status==1',
                          mincount=1):

    """
    defines a path to execute to filter the output based on a given collection (coll)
    and the presence of a min. number of objects (mincount) passing the cuts defined in basecuts
    """
    
    #gen level selection of gen jets in the endcap
    setattr(process, 'ee'+coll, cms.EDFilter(
        "CandViewShallowCloneProducer",
        src = cms.InputTag(coll),
        cut = cms.string("abs(eta)<3.0 && abs(eta)>1.479")
    ))
    setattr(process, 'goodee'+coll, cms.EDFilter(
        "CandViewSelector",
        src = cms.InputTag("ee"+coll),
        cut = cms.string(basecuts)
    ))
    setattr(process, coll+'Filter', cms.EDFilter(
        "CandViewCountFilter",
        src = cms.InputTag("goodee"+coll),
        minNumber = cms.uint32(mincount)
    ))
    setattr(process, coll+'FilterSeq', cms.Sequence(
        getattr(process,'ee'+coll)*
        getattr(process,'goodee'+coll)*
        getattr(process,coll+'Filter')
    ))
    setattr(process, coll+'FilterPath', cms.Path(
        getattr(process,coll+'FilterSeq')
    ))

    #schedule and apply selection
    filterPath=getattr(process,coll+'FilterPath')
    process.schedule.extend([filterPath])    
    process.FEVTDEBUGoutput.SelectEvents.SelectEvents=cms.vstring(filterPath.label())

    return process
