import typer
from rich import print

from vivamir.vivamir import Vivamir, FilesetKind


def command_sources(simulation: bool = False):
    """ Prints the current project's sources paths. """

    vivamir = Vivamir.search()
    if vivamir is None:
        print('[bold red]No vivamir configuration found in the current working directory.')
        return 1

    filesets = {
        FilesetKind.DES: set(fileset.path for fileset in vivamir.filesets if fileset.kind == FilesetKind.DES),
        FilesetKind.SIM: set(fileset.path for fileset in vivamir.filesets if fileset.kind == FilesetKind.SIM),
    }

    print(*sorted(filesets[FilesetKind.DES]), sep='\n')
    if simulation:
        print(*sorted(filesets[FilesetKind.SIM]), sep='\n')


def command_includes():
    """ Prints the current project's includes paths. """

    vivamir = Vivamir.search()
    if vivamir is None:
        print('[bold red]No vivamir configuration found in the current working directory.')
        return 1

    print(*vivamir.includes, sep='\n')


def command_sources_default(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    else:
        command_sources()


sources = typer.Typer(help='Prints configured sources in a machine readable way.')
sources.callback(invoke_without_command=True)(command_sources_default)
sources.command(name='sources')(command_sources)
sources.command(name='includes')(command_includes)
