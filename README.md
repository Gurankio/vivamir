Vivamir
---
A Vivado mirroring utility.

### What does this tool do?

It allows you to keep a _sane_ filesystem structure so that you can:

- edit your sources in your editor of choice;
- safely keep track of changes with your preferred VCS;
- open the Vivado GUI already configured;
- TODO: run headless operations;
- TODO: read `xsim` error logs in a readable format.

#### Example Structure

[//]: # (Source for below.)

[//]: # (https://tree.nathanfriend.com/?s=&#40;%27options!&#40;%27fancy!true~fullPath!false~trailingSlash!true~rootDot!false&#41;~G&#40;%27G%2745Ldo%2FIsrcsIsimIgen0E5workspace06A02srcH2design_18block-design.tcl7Ja-impl.v02test7tb-JFig.wcgd36BHE36CHE3E594.F**55K%27&#41;~version!%271%27&#41;2%2005*2*%203H9F04project5K*6library_7H2module_A88H*29Lmir.E...FconfGsource!H0*I04.Ja.sv8K%5CnLviva%01LKJIHGFE987654320*)

```
project/
├── vivado/
│   ├── project.srcs/
│   ├── project.sim/
│   ├── project.gen/
│   └── ...
├── workspace/
│   ├── library_A/
│   │   ├── include/
│   │   │       ...
│   │   ├── block_designs/
│   │   │   └── design1.tcl
│   │   ├── src/
│   │   │   └── module_A/
│   │   │       ├── a.sv
│   │   │       └── a-impl.v
│   │   ├── test/
│   │   │   └── module_A/
│   │   │       ├── tb-a.sv
│   │   │       └── wave.wcgd
│   │   └── vivamir.lib.toml
│   ├── library_B/
│   │   ├── ...
│   │   └── vivamir.lib.toml
│   ├── library_C/
│   │   ├── ...
│   │   └── vivamir.lib.toml
│   └── ...
├── <project.tcl>
├── <export.tcl>
└── vivamir.toml    
```

#### Usage

There are two possible flows:

1. TODO: Use the bash? script to launch Vivado and run this tool when you close the GUI.
2. Use Vivado as is, then run this tool manually to commit your changes.

> **Notice!**  
> This tool requires a shell with a Vivado executable in the PATH.   
> Source `settings64.sh` inside your Vivado installation folder to add it.

Example for Flow 2:
```sh
vivamir create

# Make sure to be in the project root for the next command.
vivado -mode batch -source project.tcl

vivamir export 'vivado -mode batch'
```

#### Install

```sh
pipx install 
```

> **Notice!**  
> Use [PipX](https://pipx.pypa.io/stable/) for simpler updates and management.   
