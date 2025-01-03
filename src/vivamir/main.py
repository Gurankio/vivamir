import typer
from rich import print

from vivamir.commands.export import command_export
from vivamir.commands.generate import command_generate
from vivamir.commands.init import command_init
from vivamir.commands.open import command_open
from vivamir.commands.remote import command_remote
from vivamir.commands.sources import sources
from vivamir.utility.version import SemanticVersion
from vivamir.vivamir import Vivamir


def commands_version():
    """ Prints the current installed Vivamir version. """

    print(f'Vivamir [blue]{SemanticVersion.project()!s}')
    # TODO: check gh for updates


def command_root():
    """ Prints the current project's root folder. """

    vivamir = Vivamir.search()
    if vivamir is None:
        print('[bold red]No vivamir configuration found in the current working directory.')
        return 1

    print(vivamir.root)


main = typer.Typer()
main.command(name='version')(commands_version)
main.command(name='root')(command_root)
main.add_typer(sources, name='list')
main.command(name='init')(command_init)
main.command(name='generate')(command_generate)
main.command(name='open')(command_open)
main.command(name='export')(command_export)
main.command(name='remote')(command_remote)

if __name__ == '__main__':
    main()
