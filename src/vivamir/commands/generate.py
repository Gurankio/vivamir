import textwrap
from pathlib import Path

from vivamir.vivamir import Vivamir, FilesetKind


def _generate_commons(vivamir: Vivamir) -> str:
    # TODO: Use Tcl namespaces.

    # Allows for sets of Path objects.
    Path.__hash__ = lambda self: hash(str(self.resolve()))

    filesets = {
        FilesetKind.DES: set(
            (fileset.path, int(fileset.read_only)) for fileset in vivamir.filesets if fileset.kind == FilesetKind.DES),
        FilesetKind.SIM: set(
            (fileset.path, int(fileset.read_only)) for fileset in vivamir.filesets if fileset.kind == FilesetKind.SIM),
    }

    block_designs = \
        '\n            '.join(f'"$::root/{bd}" \\'
                              for bd in vivamir.block_designs.trusted)
    includes = \
        '\n            '.join(f'"$::root/{file}" \\'
                              for file in sorted(map(lambda i: i.path, vivamir.includes)))
    des_filesets = \
        '\n            '.join(f'"$::root/{file}" \\'
                              for file, _ in sorted(filesets[FilesetKind.DES]))
    des_filesets_read_only = \
        '\n            '.join(f'"$::root/{file}" \\'
                              for file, read_only in sorted(filesets[FilesetKind.DES]) if read_only)
    sim_filesets = \
        '\n            '.join(f'"$::root/{file}" \\'
                              for file, _ in sorted(filesets[FilesetKind.SIM]))
    sim_filesets_read_only = \
        '\n            '.join(f'"$::root/{file}" \\'
                              for file, read_only in sorted(filesets[FilesetKind.SIM]) if read_only)
    ignores = \
        '\n            '.join(f'{file} \\'
                              for file in sorted(vivamir.ignore.list))

    return f"""
        ### Generated by vivamir.
        # Do not edit manually.
        #
        # Common procedures and variables.
        # Version 2.0.0
        
        ## Check if script is running in correct Vivado version.
        set supported_vivado_version {{{vivamir.vivado.version}}}
        set current_vivado_version [version -short]
        
        if {{ [string first $current_vivado_version $supported_vivado_version] == -1 }} {{
           puts "The version $current_vivado_version is not supported. Supported versions are $supported_vivado_version"
           return 1
        }}

        ## Close the current project
        if ![catch current_project] {{
            close_project
        }}

        ## atexit
        proc atexit {{ newbody }} {{
            if {{ [catch {{set oldbody [info body exit]}}] }} {{
                rename exit builtin_exit
                set oldbody {{ builtin_exit $returnCode }}
            }}

            proc exit {{ {{returnCode 0}} }} [subst -nocommands {{
                apply [list [list {{returnCode 0}}] [list $newbody]] \\$returnCode
                apply [list [list {{returnCode 0}}] [list $oldbody]] \\$returnCode
            }}]
        }}

        ## rglob
        proc rglob {{dirlist globlist}} {{
            set result {{}}
            set recurse {{}}
            foreach dir $dirlist {{
                    if ![file isdirectory $dir] {{
                            return -code error "'$dir' is not a directory"
                    }}
                    foreach pattern $globlist {{
                            lappend result {{*}}[glob -nocomplain -directory $dir -- $pattern]
                    }}
                    foreach file [glob -nocomplain -directory $dir -- *] {{
                            set file [file join $dir $file]
                            if [file isdirectory $file] {{
                                    set fileTail [file tail $file]
                                    if {{!($fileTail eq "." || $fileTail eq "..")}} {{
                                            lappend recurse $file
                                    }}
                            }}
                    }}
            }}
            if {{[llength $recurse] > 0}} {{
                    lappend result {{*}}[rglob $recurse $globlist]
            }}
            return $result
        }}

        ## copytree
        proc copytree {{src dst skip}} {{
            foreach file [glob -directory $src -nocomplain *] {{
                if [file isdirectory $file] {{
                    copytree $file [file join $dst [file rootname [file tail $file]]] $skip
                }} else {{
                    if {{![dict exists $skip $file]}} {{
                        puts "$file -> $dst"
                        file copy -force $file $dst    
                    }}
                }}
            }}
        }}

        ## Get root folder
        set root [file dirname [file dirname [file normalize [info script]]]]
        set root_name [file rootname [file tail $root]]

        ### From Vivamir
        set project_name {vivamir.name}
        
        set block_designs [list \\
            {block_designs}
        ]
        set includes [list \\
            {includes}
        ]
        set des_filesets [list \\
            {des_filesets}
        ]
        set des_filesets_read_only [list \\
            {des_filesets_read_only}
        ]
        set sim_filesets [list \\
            {sim_filesets}
        ]
        set sim_filesets_read_only [list \\
            {sim_filesets_read_only}
        ]
        set ignores [list \\
            {ignores}
        ]
                    
        ## Export
        proc vivamir_export_bds {{}} {{
            set block_designs_name_to_path {{}}
            foreach file $::block_designs {{
                dict set block_designs_name_to_path [file rootname [file tail $file]] $file
            }}
        
            foreach bd [get_files *.bd] {{
                set errored [catch {{
                    open_bd_design $bd
                    set name [file rootname [file tail $bd]]
                    
                    set output $::root/{vivamir.block_designs.new_design_path}/$name.tcl
                    if [dict exists $block_designs_name_to_path $name] {{
                        set output [dict get $block_designs_name_to_path $name]
                    }}
                    
                    write_bd_tcl -force $output
                    close_bd_design [current_bd_design]
                }} emsg]
                if {{$errored}} {{
                    puts $emsg
                }}
            }}
        }}
        
        proc vivamir_export_fileset {{kind {{new_file_dst $::root}}}} {{
            set ignore_files_dict {{}}
            foreach ignore $::ignores {{
                foreach file [glob -nocomplain -directory $::root -- $ignore] {{
                    dict set ignore_files_dict $file ""
                }}
            }}
        
            set skip {{}}
            foreach file [rglob $::des_filesets_read_only {{*.*}}] {{
                if {{![dict exists $ignore_files_dict $file]}} {{
                    dict set skip $file ""
                }}
            }}
            foreach file [rglob $::sim_filesets_read_only {{*.*}}] {{
                if {{![dict exists $ignore_files_dict $file]}} {{
                    dict set skip $file ""
                }}
            }}
        
            set imports [lindex [glob $::root/vivamir/project/$::project_name.srcs/$kind/imports/*] 0]
            copytree $imports $::root $skip
        
            set new_file_dst {{}}
            dict set new_file_dst sources_1 $::root/{vivamir.first_fileset(FilesetKind.DES).path}
            dict set new_file_dst sim_1 $::root/{vivamir.first_fileset(FilesetKind.SIM).path}
        
            foreach file [get_files -quiet $::root/vivamir/project/$::project_name.srcs/$kind/new/*] {{
                file copy $file [dict get $new_file_dst $kind]
            }}
        }}
    """


def _generate_project(vivamir: Vivamir) -> str:
    # TODO: configurable extensions

    # TODO: should be done at "runtime".
    setup_waveform = ''
    if waveform := next(
            (waveform
             for waveform in vivamir.first_fileset(FilesetKind.SIM).path.rglob('*.wcfg')
             if waveform.stem == vivamir.simulation_top), None
    ):
        # TODO: this does not update `current_wave_config`
        setup_waveform = f'set_property -name xsim.view -value "$::root/{waveform!s}" -object [get_filesets sim_1]'

    # TODO: configure caches.

    user_settings = \
        '\n        '.join(prop.as_tcl()
                          for prop in vivamir.vivado.properties)

    return f"""
        ### Generated by vivamir.
        # Do not edit manually.
        #
        # Creates the project.
        # Version 2.1.0
        
        ### Commons
        source commons.tcl

        ## Expand
        set ignore_files_dict {{}}
        foreach ignore $::ignores {{
            foreach file [glob -nocomplain -directory $::root -- $ignore] {{
                dict set ignore_files_dict $file ""
            }}
        }}
        
        set valid_extensions {{}}
        dict set valid_extensions .v ""
        dict set valid_extensions .vh ""
        dict set valid_extensions .sv ""
        dict set valid_extensions .svh ""
        dict set valid_extensions .vhdl ""
        
        set des_files {{}}
        foreach file [rglob $des_filesets {{*.*}}] {{
            if {{[dict exists $valid_extensions [file extension $file]] && ![dict exists $ignore_files_dict $file]}} {{
                lappend des_files $file
            }}
        }}
        
        set sim_files {{}}
        foreach file [rglob $sim_filesets {{*.*}}] {{
            if {{[dict exists $valid_extensions [file extension $file]] && ![dict exists $ignore_files_dict $file]}} {{
                lappend sim_files $file
            }}
        }}
        
        set inc_files {{}}
        foreach file [rglob $includes {{*.*}}] {{
            if {{[dict exists $valid_extensions [file extension $file]] && ![dict exists $ignore_files_dict $file]}} {{
                lappend inc_files $file
            }}
        }}
        
        ### Force create project
        create_project $project_name $::root/vivamir/project -part {vivamir.vivado.part} -force
        set -name "board_part" -value {vivamir.vivado.board_long} -objects [current_project]
        set -name "platform.board_id" -value {vivamir.vivado.board} -objects [current_project]

        ### Design files
        add_files -fileset sources_1 -norecurse $des_files
        add_files -fileset sources_1 -norecurse $inc_files
        import_files -relative_to $root -fileset sources_1
        
        ### Includes
        set includes_imported {{}}
        foreach include $includes {{
            set include_rel [string replace $include 0 [string len $::root]]
            lappend includes_imported $::root/vivamir/project/$project_name.srcs/sources_1/imports/$root_name/$include_rel
        }}
        set_property include_dirs $includes_imported [get_filesets sources_1]
        # TODO: Includes work only as globals?
        foreach include $includes_imported {{
            catch {{
                set_property is_global_include true [get_files -quiet $include/*]
            }}
        }}
        
        ### Simulation files
        add_files -fileset sim_1 -norecurse $sim_files
        import_files -relative_to $root -fileset sim_1
        
        ### Load user IPs
        set_property ip_repo_paths {f'$::root/{vivamir.ips.user_ip_repo_path}' if vivamir.ips.user_ip_repo_path.exists_in_project(vivamir) else '""'} [current_project]
        update_ip_catalog

        ### Block Designs
        foreach bd $block_designs {{
            # Source Tcl
            source -notrace $bd

            # Generate wrapper
            make_wrapper -fileset sources_1 -top [get_files ${{design_name}}.bd] 

            # Add wrapper
            add_files -fileset sources_1 "$::root/vivamir/project/${{project_name}}.gen/sources_1/bd/${{design_name}}/hdl/${{design_name}}_wrapper.v"                
        }}
        
        ### Top modules
        set_property top_lib xil_defaultlib [get_filesets sources_1]
        set_property top {{{vivamir.design_top}}} [get_filesets sources_1]
        
        set_property top_lib xil_defaultlib [get_filesets sim_1]
        set_property top {{{vivamir.simulation_top}}} [get_filesets sim_1]
        {setup_waveform}
                            
        ### User Settings
        {user_settings}

        ### Update
        update_compile_order -fileset sources_1
        update_compile_order -fileset sim_1
    """


def _generate_export(_vivamir: Vivamir) -> str:
    return f"""
        ### Generated by vivamir.
        # Do not edit manually.
        #
        # Exports BDs and sources.
        # Version 2.0.0
        
        ### Commons
        source commons.tcl
        
        ### Open project
        open_project $::root/vivamir/project/$::project_name.xpr
        
        ### Export BDs
        vivamir_export_bds
        
        ### Export sources
        vivamir_export_fileset sources_1
        vivamir_export_fileset sim_1
    """


def _generate_open(_vivamir: Vivamir) -> str:
    return f"""
        ### Generated by vivamir.
        # Do not edit manually.
        #
        # Starts the GUI after setting up a fresh project.
        # Version 2.0.0
        
        ### Create the project.
        source project.tcl
        
        ### Start GUI
        ## Export at exit (disabled due to issues with stdin on `vivamir open`)
        # atexit {{
        #     puts stdout {{Confirm export? [y/N]}}
        #     puts stdout {{This will overwrite files!}}
        #     flush stdout
        #     if {{[string first y [gets stdin]] == 0}} {{
        #         source export.tcl
        #     }}
        # }}
        
        ## Continue logging to terminal
        set pid [exec tail -n0 -f $::root/vivamir/vivado.log &]
        
        ## Wait for successful start (useful on macOS)
        while 1 {{
            set errored [catch start_gui emsg]
            if {{!$errored}} break
        
            puts [string trimright $emsg]
            puts "start_gui failed, waiting for input to retry (or close after Ctrl+C)."
            gets stdin
        }}
    """


def _generate_simulate(_vivamir: Vivamir) -> str:
    return f"""
        ### Generated by vivamir.
        # Do not edit manually.
        #
        # Runs a simulation until finish is called.
        # Version 1.0.0

        ### Create the project.
        source project.tcl

        launch_simulation
        run all
    """


def _generate_bitstream(_vivamir: Vivamir) -> str:
    # TODO: Configurable job count.
    return f"""
        ### Generated by vivamir.
        # Do not edit manually.
        #
        # Runs synthesis and implementation, creating two checkpoints.
        # Version 1.0.0

        ### Create the project.
        source project.tcl
        
        ### Synthesis
        launch_runs synth_1 -jobs 32
        wait_on_run synth_1
    
        # Save
        open_run synth_1
        write_checkpoint -force ./synth-checkpoint
        # close_run synth_1
        
        ### Implementation (to Bitstream)
        launch_runs impl_1 -jobs 32 -to_step write_bitstream
        wait_on_run impl_1
        
        # open_run impl_1
        # write_checkpoint -force ./impl-checkpoint
        # close_run impl_1
    """


def command_generate():
    """ Generates Tcl scripts based on the current configuration. """

    vivamir = Vivamir.search()
    if vivamir is None:
        print('[bold red]No vivamir configuration found in the current working directory.')
        return 1

    for filename, generate in [
        ('commons', _generate_commons),
        ('project', _generate_project),
        ('export', _generate_export),
        ('open', _generate_open),
        ('simulate', _generate_simulate),
        # ('bitstream', _generate_bitstream),
    ]:
        (vivamir.root / 'vivamir' / f'{filename}.tcl').write_text(
            textwrap.dedent(generate(vivamir)).strip() + '\n'
        )
