#include "yaml2tree.h"

int main(int argc, char* argv[]) {
  if (argc == 3) {
    yaml2tree y(argv[1]);
    y.print(atoi(argv[2]));
    return 0;
  }
  if (argc == 2) {
    yaml2tree y(argv[1]);
    y.print();
    return 0;
  }
  std::cout << "usage: ./dumpyaml [yaml file] ([verbose=<0|1>])" << std::endl;
  return 1;
}

