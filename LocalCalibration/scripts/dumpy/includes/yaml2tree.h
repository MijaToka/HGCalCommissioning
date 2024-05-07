#include <iostream>
#include <iomanip>
#include <fstream>
#include <vector>
#include <string>

#include "xjjcuti.h"

// enum { dir, tree, branch };
struct node {
  int type, mom, layer;
  std::string name;
  int islast = 0;
};

class yaml2tree {
public:
  yaml2tree(std::string input_name);
  void print(bool v = true);
private:
  std::string filename;
  bool verbose;
  std::vector<node> tr;
  void enterdir(int source);
  std::vector<int> child_list(int j);
  void findmom(int layer, int ilast, int& mom);
  void drawlines(int i);
  std::vector<std::string> classname = { "dict", "list", "var" };
};

void yaml2tree::print(bool v) {
  verbose = v;
  enterdir(-1);
  std::cout<<std::endl;
}

void yaml2tree::enterdir(int source) {

  if(source==-1) { std::cout << std::endl << "   \e[2m("<<xjjc::str_divide_lastel(filename, "/")<<")\e[0m" << std::endl
                             << "   \e[1m./\e[0m"<<std::endl; }

  auto childrens = child_list(source);
  for (auto ii : childrens) {
    auto grandchild = child_list(ii);
    if (!verbose && tr[ii].type >= 2) continue;

    drawlines(source);
    std::cout << "\e[0m"<< (tr[ii].islast?"\u2514":"\u251C") << "\u2500\u2500\e[0m"
              << (tr[ii].type==2?" \e[34m(":" \e[32m(") << classname[tr[ii].type] << ")\e[0m"
              << " \e[2m=>\e[0m "
              << (tr[ii].type==2?"\e[2m":"\e[1m") << tr[ii].name << "\e[0m";
    if(tr[ii].type == 1) { 
      std::cout << " \e[33m[" << grandchild.size() << "]\e[0m"; 
    }
    std::cout<<std::endl;

    if (tr[ii].type == 0) { enterdir(ii); }
    else if (tr[ii].type == 1 && !grandchild.empty()) { enterdir(grandchild[0]); }
  }
}

void yaml2tree::findmom(int layer, int ilast, int& mom) {
  if (ilast >= 0) {
    if (layer > tr[ilast].layer) {
      mom = ilast;
    } else {        
      while (layer <= tr[mom].layer) {
        mom = tr[mom].mom;
        if (mom < 0) break;
      }
    }
  }
}

std::vector<int> yaml2tree::child_list(int j) {
  std::vector<int> list;
  for (long unsigned int i=0; i<tr.size(); i++) {
    if (tr[i].mom == j) {
      list.push_back(i);
    }
  }
  if (list.size() > 0)
    tr[list.back()].islast = 1;
  else {
    tr[j].type = 2;
  }
  return list;
}

void yaml2tree::drawlines(int i) {
  std::vector<int> islast;
  while (i >= 0) {
    if (tr[i].type == 1 && !islast.empty()) {
      islast.erase(islast.begin(), islast.begin()+1);
    }
    islast.insert(islast.begin(), tr[i].islast);
    i = tr[i].mom;
  }
  std::cout<<"   ";
  for (auto j : islast) {
    std::cout<<(j?" ":"\u2502")<<"   ";
  }
}

yaml2tree::yaml2tree(std::string input_name) :
  filename(input_name) {
  std::ifstream getdata(filename.c_str());

  std::string line;
  int mom = -1, nstruc = -1;
  while (!getdata.eof()) {
    std::getline(getdata, line);
    if (line == "") continue;

    // std::cout<<line<<std::endl;

    int ilast = tr.size() - 1;
    int layer = 0, type = 0, finstruc = 0;
    while (line[0] == ' ' || line[0] == '-') {
      layer++;
      if (line[0] == '-') { nstruc++; finstruc++; }
      line.erase(0, 1);
    }
    layer /= 2;
    if (nstruc >= 0 && !finstruc) {
      layer++;
      if (layer < tr[ilast].layer) {
        nstruc = -1;
        layer--;
      }
    }

    line = xjjc::str_erasestar(line, ":*");
    if (xjjc::str_isinteger(line)) type = 1;

    findmom(layer, ilast, mom);
    
    if (finstruc) {
      node n_addition = {0 /*type*/, mom, layer, std::to_string(nstruc)};
      tr.push_back(n_addition);
      tr[mom].type = 1;
      mom = tr.size() - 1;
      layer++;
    }
    
    node n;
    n.name = line;
    n.layer = layer;
    n.type = 0;
    n.mom = mom;
    if (mom >= 0) {
      tr[mom].type = type;
    }

    // if (line == "idcode") std::cout<<type<<std::endl;
    
    tr.push_back(n);
   
  }

  // for (long unsigned int i=0; i<tr.size(); i++) {
  //   if (i>50) break;
  //   std::cout<<std::left
  //            <<std::setw(6)<<i
  //            <<std::setw(3)<<tr[i].layer
  //            <<std::setw(6)<<tr[i].mom
  //            <<std::setw(3)<<tr[i].type
  //            <<tr[i].name<<std::endl;
  // }

  // std::cout<<tr.size()<<std::endl;
}

