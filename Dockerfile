FROM gitlab-registry.cern.ch/cms-cloud/cmssw-docker/al9-cms

ARG CMS_PATH=/cvmfs/cms.cern.ch
ARG CMSSW_RELEASE=CMSSW_15_1_0_pre1
ARG SCRAM_ARCH=el9_amd64_gcc11

SHELL ["/bin/bash", "-c"]

WORKDIR /code

RUN shopt -s expand_aliases && \
    set +u && \
    source ${CMS_PATH}/cmsset_default.sh; set -u && \
    cmsrel ${CMSSW_RELEASE} && \
    cd ${CMSSW_RELEASE}/src && \
    cmsenv 

COPY . /code/${CMSSW_RELEASE}/src/HGCalCommissioning

RUN shopt -s expand_aliases && \
    set +u && \
    source ${CMS_PATH}/cmsset_default.sh; set -u && \
    cd ${CMSSW_RELEASE}/src && \
    cmsenv && \
    scram b

