# ezhdl

**ezhdl** is an attempt to port the VHDL FPGA programming language to python, while at the same time adding a number of quality-of-life improvements.

At the moment the library is solely focused on simulating synthesizable logic, in order to facilitate high level development and testing before porting the implementation to VHDL or Verilog.

## Roadmap
The plan going forward is to make the ezhdl simulator compatible with CoCoTB, as well as implementing a converter to Verilog and/or VHDL. By doing so it will be possible to run CoCoTB testcases against both the ezhdl implementation and the translated Verilog/VHDL, thus completely validating the conversion process. At the same time the converted Verilog/VHDL can be treated as an "intermediate" compilation product and imported into an FPGA project to be finally synthesized and used on real hardware.

## Examples
**ezhdl** was originally developed to facilitate simulation and debugging of an FPGA implementation of the VIC-II graphics chip found in the Commodore-64 computer. For the time being that project will serve as the main example of practical use of **ezhdl**: [vicii-passive](https://github.com/sideprojectslab/vicii-passive)
