import subprocess

import typer
from rich import print
from typing import List

from vivamir.vivamir import Vivamir


def command_export(vivado_executable: List[str], yes: bool = False):
    """ Runs Vivado to export BDs and sources. """

    vivamir = Vivamir.search()
    if vivamir is None:
        print('[bold red]No vivamir configuration found in the current working directory.')
        return 1

    if not yes:
        print('[bold orange]This command will overwrite files!')
        all_good = typer.confirm('Is the VCS all good?', default=False)
        # TODO: git integration?

        if not all_good:
            print('Aborted.')
            return

    subprocess.run([
        *vivado_executable, '-mode', 'batch', '-source', 'export.tcl'
    ], cwd=vivamir.root / 'vivamir', check=True)

    print('[green]Done!')
    print('  Check VCS for imports changes.')
