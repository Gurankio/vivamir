import dataclasses
import json
import shutil
import subprocess
import tempfile
import textwrap
from decimal import Decimal
from enum import Enum
from functools import cache, reduce
from itertools import chain
from pathlib import Path

import sys
from typing import Optional

import typer
from rich import print
import tomllib
import dacite

# Allow for sets of Path objects.
Path.__hash__ = lambda self: hash(str(self))

main = typer.Typer()

SRC = Path(__file__).parent


@dataclasses.dataclass()
class BlockDesign:
    library_path: Path


class FilesetKind(Enum):
    DES = 'des'
    SIM = 'sim'

    @property
    def vivado_name(self) -> str:
        return {
            FilesetKind.DES: 'sources_1',
            FilesetKind.SIM: 'sim_1',
        }[self]

    def __str__(self):
        return {
            FilesetKind.DES: 'Design',
            FilesetKind.SIM: 'Simulation',
        }[self]


@dataclasses.dataclass()
class Fileset:
    kind: FilesetKind
    library_path: Path


@dataclasses.dataclass()
class Include:
    library_path: Path


@dataclasses.dataclass()
class Library:
    filesets: list[Fileset]
    includes: Optional[list[Include]]
    block_designs: Optional[list[BlockDesign]]

    def first_fileset(self, kind: FilesetKind) -> Optional[Fileset]:
        return next(f for f in self.filesets if f.kind == kind)


@main.command(name='init')
def command_init():
    project = Path.cwd()

    if len([*project.rglob('*')]) != 0:
        print('[bold red]Not in an empty directory.')
        sys.exit(1)

    main = None
    while main is None:
        main = typer.prompt('Base library name', project.name)

        if ' ' in main:
            print('[bold red]Library name cannot contain spaces.')
            main = None
            continue

    DEFAULT_PROJECT = (SRC / 'project-default.toml')
    DEFAULT_LIBRARY = (SRC / 'library-default.toml')
    defaults = dacite.from_dict(
        Library, tomllib.loads(DEFAULT_LIBRARY.read_text().format(project.name, main, 'vivado'), parse_float=Decimal),
        dacite.Config(strict=True, cast=[float, Enum, Path]),
    )

    # Project configuration.
    shutil.copyfile(DEFAULT_PROJECT, project / 'vivamir.toml')

    # .gitignore
    DEFAULT_IGNORE = (SRC / 'ignore-default.txt')
    shutil.copyfile(DEFAULT_IGNORE, project / '.gitignore')

    # Main library.
    library_path = project / 'workspace' / main
    library_path.mkdir(parents=True)
    shutil.copyfile(DEFAULT_LIBRARY, library_path / 'vivamir.lib.toml')
    for file in defaults.filesets:
        (library_path / file.library_path).mkdir(parents=True, exist_ok=True)

    # TODO: git?

    print('[green]Done!')


# open = typer.Typer(name='open')
#
#
# @open.command(name='bd')
# def command_block_design(name: str):
#     ...
#
#
# @open.command(name='sim')
# def command_sim(sim_files: list[Path] = [*Path.cwd().rglob('*')]):
#     sim_files = [file.resolve(strict=True) for file in sim_files]
#
#     cwd = Path.cwd()
#     ignore = set()
#
#     workspace = cwd.parent / 'auto-thingy.json'
#     # print(workspace)
#     if workspace.exists():
#         # print('asd')
#         workspace = json.loads(workspace.read_text())
#         # print(workspace)
#         ignore.update((str((cwd.parent / Path(file)).relative_to(cwd, walk_up=True))
#                        for file in workspace['ignore']))
#         # print(ignore)
#
#     def lookup_files(package):
#         meta = json.loads((cwd.parent / package / 'auto-thingy.json').read_text())
#         files = (str((cwd.parent / package / Path(file)).relative_to(cwd, walk_up=True))
#                  for file in meta['files'])
#         return [*chain(files, *(lookup_files(dep) for dep in meta['dependencies']))]
#
#     def lookup_includes(package):
#         meta = json.loads((cwd.parent / package / 'auto-thingy.json').read_text())
#         includes = (str((cwd.parent / package / Path(file)).relative_to(cwd, walk_up=True))
#                     for file in meta['include_dirs'])
#         return [*chain(includes, *(lookup_includes(dep) for dep in meta['dependencies']))]
#
#     self = json.loads((cwd / 'auto-thingy.json').read_text())
#     files = set(chain(self['files'], *(lookup_files(dep) for dep in self['dependencies'])))
#     files = sorted(files.difference(ignore))  # Remove ignored files.
#
#     top_module = '${BD_name}_wrapper' if len(sim_files) == 0 else sim_files[0].stem
#
#     sim_files = sorted(set(str(file.relative_to(cwd, walk_up=True))
#                            for file in sim_files))
#
#     includes = sorted(set(chain(self['include_dirs'], *(lookup_includes(dep) for dep in self['dependencies']))))
#
#     # Taken from "xilinx.mk"
#     # XILINX_BOARD      ?= kr260_som
#     # XILINX_PART       := xck26-sfvc784-2LV-c
#     # XILINX_BOARD_LONG := xilinx.com:kr260_som:part0:1.1
#
#     (cwd / 'bd-design_1.tcl').touch(exist_ok=True)
#
#     # TODO: also track waveforms configs
#     # add_files -fileset sim_1 -norecurse /pwd/tb_axi_rt_bd1_behav.wcfg
#     # set_property xsim.view /pwd/tb_axi_rt_bd1_behav.wcfg [get_filesets sim_1]
#     # OR this below?
#     # open_wave_config {/pwd/tb_axi_rt_bd1_behav.wcfg}
#
#     (cwd / 'bd-ready.tcl').write_text(textwrap.dedent(f"""
#         # Check if script is running in correct Vivado version.
#         set scripts_vivado_version "2022.2"
#         set current_vivado_version [version -short]
#
#         if {{ [string first $current_vivado_version $scripts_vivado_version] == -1 }} {{
#            puts "The version $current_vivado_version is not supported. Supported versions are $scripts_vivado_version"
#            return 1
#         }}
#
#         # From auto-thingy
#         set project_name {cwd.name}
#         set files [list \\
#             {'\n            '.join(f'"{file}" \\' for file in files)}
#         ]
#         set sim_files [list \\
#             {'\n            '.join(f'"{file}" \\' for file in sim_files)}
#         ]
#         set includes [list \\
#             {'\n            '.join(f'"{dir}" \\' for dir in includes)}
#         ]
#         set includes_imported [list \\
#             {'\n            '.join(f'"/tmp/$project_name/$project_name.srcs/sources_1/imports/workspace/{cwd.name}/{dir}" \\' for dir in includes)}
#         ]
#
#         # Create a new project
#         create_project $project_name /tmp/$project_name -part xck26-sfvc784-2LV-c -force
#         # set_property target_language Verilog [current_project]
#
#         # Add design files
#         # create_fileset -srcset sources_1
#         add_files -fileset sources_1 -norecurse -scan_for_includes $files
#         add_files -fileset sources_1 $includes
#         import_files -fileset sources_1
#         set_property include_dirs $includes_imported [get_filesets sources_1]
#
#         # Add simulation files
#         # create_fileset -simset sim_1
#         # add_files -fileset sim_1 -norecurse $files
#         add_files -fileset sim_1 -norecurse $sim_files
#         # add_files -fileset sim_1 $includes
#         import_files -fileset sim_1
#         set_property include_dirs $includes_imported [get_filesets sim_1]
#
#         ### Top Block Design
#         set BD_name design_1
#
#         # Create the Block Design
#         create_bd_design $BD_name
#         common::send_msg_id "BD_TCL-004" "INFO" "Making design <$BD_name> as current_bd_design."
#         current_bd_design $BD_name
#
#         source bd-design_1.tcl
#
#         # Validate the BD
#         regenerate_bd_layout
#         validate_bd_design
#         save_bd_design
#
#         # Generate the wrapper
#         make_wrapper -files [get_files ${{BD_name}}.bd] -top
#
#         # Add the wrapper to the fileset
#         add_files -norecurse -fileset sources_1 [list \\
#             "[file normalize [glob "/tmp/$project_name/$project_name.gen/sources_1/bd/$BD_name/hdl/${{BD_name}}_wrapper.v"]]" \\
#         ]
#
#         # Set top modules and update
#         set_property top ${{BD_name}}_wrapper [current_fileset]
#         update_compile_order -fileset sources_1
#
#         set_property top {top_module} [get_filesets sim_1]
#         # set_property top_lib xil_defaultlib [get_filesets sim_1]
#         update_compile_order -fileset sim_1
#
#         # Start GUI
#         start_gui
#         # open_bd_design {{/tmp/axi_rt/axi_rt.srcs/sources_1/bd/design_1/design_1.bd}}
#         open_wave_config {{/pwd/tb_axi_rt_bd1_behav.wcfg}}
#         # No need to launch_sim the above does it: the target is also implicit in project mode i guess
#         # launch_simulation -simset sim_1 -type behavioral
#     """).strip())


@dataclasses.dataclass()
class Project:
    name: str
    main: str
    design_top: Optional[str]
    simulation_top: Optional[str]
    ignore: Optional[set[Path]]

    def main_library(self, root) -> tuple[Path, Library]:
        return next((p, l) for p, l in find_libraries(root)
                    if p.name == self.main)


@dataclasses.dataclass()
class Vivado:
    path: Path


@dataclasses.dataclass()
class Vivamir:
    project: Project
    vivado: Vivado


@cache
def find_root() -> Optional[tuple[Path, Vivamir]]:
    root = Path.cwd()
    while not (root / 'vivamir.toml').exists():
        if root.parent == root:
            return None
        else:
            root = root.parent

    vivamir = dacite.from_dict(
        Vivamir, tomllib.loads((root / 'vivamir.toml').read_text(), parse_float=Decimal),
        dacite.Config(strict=True, cast=[float, set, Enum, Path]),
    )

    if vivamir.project.ignore is None:
        vivamir.project.ignore = set()

    # Normalize all files.
    vivamir.project.ignore = set(chain(*[(root / 'workspace').glob(str(file)) for file in vivamir.project.ignore]))
    vivamir.project.ignore = set(file.relative_to(root) for file in vivamir.project.ignore)
    return root, vivamir


@main.command(name='root')
def command_root():
    print(find_root()[0])


@cache
def find_libraries(root: Path) -> list[tuple[Path, Library]]:
    def load(path: Path) -> Library:
        library = dacite.from_dict(
            Library, tomllib.loads(path.read_text(), parse_float=Decimal),
            dacite.Config(strict=True, cast=[float, set, Enum, Path]),
        )
        if library.includes is None:
            library.includes = []
        if library.block_designs is None:
            library.block_designs = []
        return library

    return [(path.parent, load(path)) for path in
            (root / 'workspace').glob('*/vivamir.lib.toml')]


@main.command(name='create')
def command_create():
    root, vivamir = find_root()
    workspace = root / 'workspace'

    includes = set()
    block_designs = []
    filesets = {
        FilesetKind.DES: set(),
        FilesetKind.SIM: set(),
    }

    for path, library in find_libraries(root):
        includes.update((path / target.library_path).resolve(strict=True).relative_to(root)
                        for target in library.includes)

        # TODO: make fully general.
        if path.name == vivamir.project.main:
            for bds in library.block_designs:
                for bd in (path / bds.library_path).resolve(strict=True).rglob('*.tcl'):
                    block_designs.append((bd.stem, bd.relative_to(root)))

        for fileset in library.filesets:
            filesets[fileset.kind].update(
                file.relative_to(root)
                for file in (path / fileset.library_path).resolve(strict=True).rglob('*.*')
            )

    filesets[FilesetKind.DES] = filesets[FilesetKind.DES].difference(vivamir.project.ignore)
    filesets[FilesetKind.SIM] = filesets[FilesetKind.SIM].difference(vivamir.project.ignore)

    # Taken from "xilinx.mk"
    # TODO: should be project parameters
    # XILINX_BOARD      ?= kr260_som
    # XILINX_PART       := xck26-sfvc784-2LV-c
    # XILINX_BOARD_LONG := xilinx.com:kr260_som:part0:1.1
    # VERSION := 2022.2

    (root / 'project.tcl').write_text(textwrap.dedent(f"""
            ### Generated by vivamir.
            # Do not edit manually.
    
            ### Check if script is running in correct Vivado version.
            set scripts_vivado_version "2022.2"
            set current_vivado_version [version -short]

            if {{ [string first $current_vivado_version $scripts_vivado_version] == -1 }} {{
               puts "The version $current_vivado_version is not supported. Supported versions are $scripts_vivado_version"
               return 1
            }}
            
            ### Get script folder
            namespace eval _tcl {{
                proc get_script_folder {{}} {{
                    set script_path [file normalize [info script]]
                    set script_folder [file dirname $script_path]
                    return $script_folder
                }}
            }}
            variable root
            set root [_tcl::get_script_folder]

            ### From Vivamir
            set project_name {vivamir.project.name}
            set project_main {vivamir.project.main}
            set des_files [list \\
                {'\n                '.join(f'"{file}" \\' for file in sorted(filesets[FilesetKind.DES]))}
            ]
            set sim_files [list \\
                {'\n                '.join(f'"{file}" \\' for file in sorted(filesets[FilesetKind.SIM]))}
            ]
            set includes [list \\
                {'\n                '.join(f'"{file}" \\' for file in sorted(includes))}
            ]
            set includes_imported [list \\
                {'\n                '.join(f'"$root/{'vivado'}/${{project_name}}.srcs/sources_1/imports/{dir}" \\'
                                           for dir in sorted(includes))}
            ]

            ### Create a new project
            create_project $project_name $root/{'vivado'} -part xck26-sfvc784-2LV-c -force
            # set_property target_language Verilog [current_project]

            ### Add design files
            add_files -fileset sources_1 -norecurse $des_files
            add_files -fileset sources_1 $includes
            import_files -fileset sources_1
            set_property include_dirs $includes_imported [get_filesets sources_1]
            # TODO: Includes work only when marked as globals?
            {'\n            '.join(f'set_property is_global_include true [get_files $::root/vivado/$::project_name.srcs/sources_1/imports/{file}/*]' for file in includes)}
            # update_compile_order -fileset sources_1

            ### Add simulation files
            add_files -fileset sim_1 -norecurse $sim_files
            import_files -fileset sim_1
            # update_compile_order -fileset sim_1

            ### Block Design
            proc vivamir_block_design {{name source}} {{
                puts "Creating block design: $name"
            
                # Create the Block Design
                create_bd_design $name
                current_bd_design $name
    
                source -notrace $source
            
                # Validate the BD
                regenerate_bd_layout
                validate_bd_design 
                save_bd_design
    
                # Generate the wrapper
                make_wrapper -fileset sources_1 -top [get_files ${{name}}.bd] 
    
                # Add the wrapper to the fileset
                add_files -norecurse -fileset sources_1 [list \\
                    "[file normalize [glob "$::root/{'vivado'}/$::project_name.gen/sources_1/bd/$name/hdl/${{name}}_wrapper.v"]]" \\
                ]
            }}
                
            {'\n            '.join(f'vivamir_block_design {name} {source}'
                                   for name, source in block_designs)}
                
            ### Set top modules and Update
            set_property top_lib xil_defaultlib [get_filesets sources_1]
            {f'set_property top {vivamir.project.design_top} [get_filesets sources_1]' if vivamir.project.design_top is not None else ''}
            # update_compile_order -fileset sources_1
            
            set_property top_lib xil_defaultlib [get_filesets sim_1]
            {f'set_property top {vivamir.project.simulation_top} [get_filesets sim_1]' if vivamir.project.simulation_top is not None else ''}
            # update_compile_order -fileset sim_1
            
            update_compile_order
                
            # Start GUI
            start_gui
        """).strip())

    (root / 'veridian.yml').write_text(textwrap.dedent(f"""
        # List of directories with header files
        include_dirs:
        {'\n        '.join(f'  - "{file}"' for file in includes)}

        # List of directories to recursively search for SystemVerilog/Verilog sources
        source_dirs:
        {'\n        '.join(f'  - "{file}"' for file in set(file.parent for file in chain(*(filesets[FilesetKind.DES], filesets[FilesetKind.SIM]))))}
    """).strip())


@main.command(name='export')
def command_export(vivado_batch: str, block_designs: bool = True):
    print('[bold red]This command will overwrite files in the workspace!')
    all_good = typer.confirm('Is the VCS all good?', default=False)

    if not all_good:
        print('Aborted.')
        return

    root, vivamir = find_root()
    vivado_root = root / 'vivado'

    tempfile.NamedTemporaryFile()

    bd_existing = vivado_root / f'{vivamir.project.name}.srcs' / 'sources_1' / 'bd'
    bd_target = vivamir.project.main_library(root)[1].block_designs[0].library_path

    (root / 'export.tcl').write_text(textwrap.dedent(f"""
            # Check if script is running in correct Vivado version.
            set scripts_vivado_version "2022.2"
            set current_vivado_version [version -short]

            if {{ [string first $current_vivado_version $scripts_vivado_version] == -1 }} {{
               puts "The version $current_vivado_version is not supported. Supported versions are $scripts_vivado_version"
               return 1
            }}
            
            # From Vivamir
            set project_name {vivamir.project.name}

            # Open project
            open_project {'vivado'}/$project_name
            
            proc vivamir_block_design {{bd}} {{
                set errored [catch {{
                    open_bd_design [file normalize ./vivado/$::project_name.srcs/sources_1/bd/$bd/$bd.bd]
                    write_bd_tcl -force [file normalize ./workspace/axi_rt/block_designs/$bd.tcl]
                }} msg]
                if {{$errored}} {{
                    puts "-> $bd failed!"
                    puts "   ( $errored): $msg"
                }} else {{
                    puts "-> $bd successfully exported."
                }}
                puts ""
            }}

            {'\n            '.join(f'vivamir_block_design {bd.stem}'
                                   for bd in bd_existing.glob('*/*.bd'))}
        """).strip())

    if block_designs:
        subprocess.run([
            vivado_batch, '-source', 'export.tcl'
        ], cwd=root)

        for bd in bd_target.glob('*.tcl'):
            useless_warning = ('\n'
                               'common::send_gid_msg -ssname BD::TCL -id 2052 -severity "CRITICAL WARNING"'
                               ' "This Tcl script was generated from a block design that is out-of-date/locked.'
                               ' It is possible that design <$design_name> may result in errors during construction."\n'
                               '\n')
            bd.write_text(bd.read_text().replace(useless_warning, '').strip() + '\n')
    else:
        print('[dim]Block designs skipped.')

    filesets = {
        FilesetKind.DES: set(),
        FilesetKind.SIM: set(),
    }

    for path, library in find_libraries(root):
        for fileset in library.filesets:
            filesets[fileset.kind].update(
                file.relative_to(root)
                for file in (path / fileset.library_path).resolve(strict=True).rglob('*.*')
            )

    def find_common(files):
        dirs = set(file for file in files)
        levels = [(i, p) for dir in dirs for i, p in enumerate(dir.parts)]
        mapping = {}
        for i, p in levels:
            if i not in mapping:
                mapping[i] = set()
            mapping[i].add(Path(p))
        for i, parts in mapping.items():
            if len(parts) > 1:
                return reduce(lambda a, b: a / b, (next(iter(mapping[j])) for j in range(i)))
        else:
            raise NotImplemented

    for kind, fileset in filesets.items():
        common = find_common(fileset)
        # Intentionally keep only the last folder, Vivado does this to make everything harder.
        vivado_common = common.name
        imported = vivado_root / f'{vivamir.project.name}.srcs' / kind.vivado_name / 'imports' / vivado_common

        if imported.exists():
            shutil.copytree(src=imported, dst=(root / common), dirs_exist_ok=True)
        else:
            print(f'[bold red]Error:[/] Unexpected common root!')
            print(f'  {kind!s} files skipped.')
            print(f'  Look manually for changes here: {imported.parent!s}')

        new = vivado_root / f'{vivamir.project.name}.srcs' / kind.vivado_name / 'new'
        if new.exists():
            default_fileset = vivamir.project.main_library(root)[1].first_fileset(kind).library_path
            dst = (root / 'workspace' / vivamir.project.main / default_fileset)

            for file in new.rglob('*.*'):
                shutil.copyfile(src=file, dst=dst / file.name)

    print('[green]Done!')
    print('  Check VCS for imported changes.')


if __name__ == '__main__':
    main()
