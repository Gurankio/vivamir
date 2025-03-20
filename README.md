Vivamir
---
A Vivado mirroring utility.

### Installation

Use [PipX](https://pipx.pypa.io/stable/) for simpler updates and venv management.

```sh
pipx install git+https://git@github.com/Gurankio/vivamir
```

Experimental: a python3.8 compatible version is available in the python3.8 branch
and can be installed with the following:

```sh
pipx install git+https://git@github.com/Gurankio/vivamir@python3.8
```

### What does this tool do?

It allows you to:

- keep a _sane_ filesystem structure so that you can keep track of changes with your preferred VCS;
- open the Vivado GUI in a consistent state;
- TODO: run headless operations on remote hosts;
- TODO: actually read logs.

#### Example project structure

[//]: # (Tool for below: https://tree.nathanfriend.com)

```
project-name/
├── vivamir/
│   ├── .gitignore
│   ├── project.tcl
│   ├── export.tcl
│   ├── ... (other Tcl scripts)
│   └── project/
│       ├── project.srcs/
│       ├── project.sim/
│       ├── project.gen/
│       └── ... (other Vivado files)
├── ips/
│   └── wrapper_A/
│       ├── ... (your IPs, see TODO)
│       └── component.xml
├── block_designs/
│   ├── design_1.tcl
│   └── design_1/
│       ├── design_1.v
│       └── ... (external IP files, TODO)
├── src/
│   └── module_A/
│       ├── a.sv
│       └── a-impl.v
├── test/
│   └── module_A/
│       ├── tb-a-top.sv
│       ├── wave-config.wcgd
│       └── vivamir.target.yaml
├── vivamir.toml
└── vivamir.ignore
```

### Usage

> **Notice!**  
> This tool requires a shell with a Vivado executable in the PATH.   
> Source `settings64.sh` inside your Vivado installation folder to add it.

There are two possibilities:

1. Use `vivamir open` command to launch Vivado and (automatically) sync when you close the GUI.
2. Use Vivado as is and run the generated scripts manually (`cd` to the vivamir folder first):
    - Use `project.tcl` to create a fresh project;
    - Use `export.tcl` to export sources and BDs.

Example commands:

```sh
vivamir generate

# Make sure to be in the vivamir folder the next commands.
vivado -mode tcl -source project.tcl
> start_gui

vivado -mode tcl -source export.tcl

```

### Vivado Explained

In this section I will try my best to summarize how the scripts work.

#### Tcl Language

The available Tcl language is quite powerful and has good enough utilities for most scripts regarding file management.
The syntax is considerably different from most modern languages but this
[short manual page gives a pretty good introduction](https://www.tcl.tk/man/tcl8.5/TclCmd/Tcl.htm).

Running Vivado in Tcl mode also gives a simple repl which can be used to test snippets
and learn available commands through tab completion.

Of notice are:

- `file tail` to get a file's name (like `basename` would);
- `file rootname` to get a file's stem;
- `file dirname` to get a file's directory;
- `string first` to check if two string have the same prefix;
- `exec` to run arbitrary shell commands.

For more information Tcl's builtin commands see the [Tcler's Wiki](https://wiki.tcl-lang.org/page/file),
here linked for the file command.

#### Vivado's jargon

Fileset: a collection of files that can be used either for synthesis (`sources_1`) or simulation (`sim_1`).
Block Diagram: allows you to wire together Packaged IPs and Modules and export them as Verilog modules.  
Modules: a plain Verilog file that can be imported in a block design as if it were a fully packaged IP,
with caveats see below.    
Packaged IP: a collection of files that can be shared as a read-only black-box.

#### File management

To create a project there are two key steps:

1. Adding files to filesets;
2. Importing those files.

Adding files does not copy anything and merely adds those files to Vivado's tools,
while importing actually makes a copy inside the project folder.

Vivado remembers the original added file location, even after importing, as such the `reimport_files` command
can be used to quickly import changes made in the original files to an open project.

This cannot be used for newly created files, as those need to be added first.
TODO: a special vivamir command should be available in the Tcl shell to search for files again.

> Importing is necessary to make modules in block designs work as Vivado cannot create a module with non-imported files.

#### Modules or Packaged IPs?

Ideally both would have the same features, but alas they do not.
(_I work with Vivado 2022.2 might have changed in later releases._)

Mainly Modules have considerable restrictions:

- AXI ports can only be masters or slaves, no monitors;
- there is no way to declare a configurable array of AXI ports (but you can for am hard-coded amount);
- there is no way to have AXI parameters propagate like Xilinx's own IPs do.

Notably ~~these restriction are not readily available~~ only the last restriction requires custom Tcl scripts to work.
(
_TODO: See some side project of mine that makes wrapping stuff easy._
I managed to get a configurable array of AXI monitor ports easily and might also work without duplicating files.
Still likely needs some script to help with re-packaging at every change...
)

Should you package something you will have to duplicate all required files!
Example:
You have file A, B, C and need to package A who depends on B.    
Suppose that C also depends on B.  
You will end up creating a folder with A and a copy of B.  
Now you have 2 copies of B! Nice.

And to make everything more pleasurable, every time you update **any** file that is used by an IP you will have to:

1. Open the IP in a temporary project
   (Vivado does this for you quite well surprisingly, right-click on your IP in a block diagram, then "edit IP");
2. Re-package your IP through the interface or scripts;
3. Close the temporary project.
4. Run "IP status report" (Vivado will complain about this as soon as you close the project);
5. Update the IP through the menu that comes up;
6. Regenerate the BD just to be sure.

Have fun packaging your files!
