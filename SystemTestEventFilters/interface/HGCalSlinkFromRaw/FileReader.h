#ifndef hgcal_slinkfromraw_FileReader_h
#define hgcal_slinkfromraw_FileReader_h

#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "RecordPrinter.h"

#include <iostream>
#include <fstream>
#include <sstream>



namespace hgcal_slinkfromraw {
  
  class FileReader {
  public:

    FileReader() {};
    
    inline bool open(const std::string &f) {
      _inputFile.open(f,std::ios::binary);
      _fileName = f;
      if (_inputFile.fail())
	throw cms::Exception("hgcal_slinkfromraw::FileReader::open") 
	  << "Failed to open file " << f;
      return (_inputFile?true:false);
    }
    
    inline bool read(Record *h) {
      _inputFile.read((char*)h,8);
      
      if(!_inputFile) return false; 
      _inputFile.read((char*)(h+1),8*h->payloadLength());
      
      return true;
    }
    
    inline bool close() {
      if(_inputFile.is_open()) {
	edm::LogInfo("hgcal_slinkfromraw::FileReader::open") << 
	  "FileReader::close() closing file " << _fileName;
	_inputFile.close();
      }
      return true;
    }
    
    inline bool closed() {
      return !_inputFile.is_open();
    }
    
  protected:
    std::string _fileName;
    std::ifstream _inputFile;
  };
}

#endif
