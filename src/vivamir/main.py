import subprocess
from time import sleep
from typing import Iterator

import typer
from rich import print

from vivamir.commands.generate import command_generate
from vivamir.commands.init import command_init
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


def _follow(file, sleep_sec=0.125) -> Iterator[str]:
    """ Yield each line from a file as they are written.
    `sleep_sec` is the time to sleep after empty reads. """
    line = ''
    while True:
        tmp = file.readline()
        if tmp is not None and tmp != "":
            line += tmp
            while '\n' in line:
                out, line = line.split('\n', 1)
                yield out
        elif sleep_sec:
            sleep(sleep_sec)


def command_open(vivado_executable: list[str]):
    """ Runs Vivado and opens the GUI with a fresh project. """

    vivamir = Vivamir.search()
    if vivamir is None:
        print('[bold red]No vivamir configuration found in the current working directory.')
        return 1

    print('INFO: [Vivamir] Regenerating scripts...')
    command_generate()

    process = None

    try:
        logfile = vivamir.root / 'vivamir' / 'vivado.log'
        logfile.unlink(missing_ok=True)

        process = subprocess.Popen(
            args=[
                *vivado_executable, '-mode', 'batch', '-source', 'open.tcl'
            ],
            cwd=vivamir.root / 'vivamir',
            text=True,
            # universal_newlines=True,
            # bufsize=16,
            # stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            # stdin=sys.stdin,
        )

        print('INFO: [Vivamir] Vivado started.')

        while not logfile.exists():
            sleep(0.250)

        with open(logfile, 'rt') as log:
            log = _follow(log)
            i = 0
            while process.poll() is None:
                print('a')
                i += 1

    finally:
        if process is not None:
            try:
                print('INFO: [Vivamir] Awaiting Vivado termination.')
                out, err = process.communicate(timeout=30)
                if out is not None:
                    print(out)
                if err is not None:
                    print(err)
            except (KeyboardInterrupt, subprocess.TimeoutExpired):
                process.kill()
                print('INFO: [Vivamir] Vivado terminated forcefully.')
            else:
                print('INFO: [Vivamir] Vivado terminated.')


def command_export(vivado_executable: list[str], yes: bool = False):
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


def command_remote():
    """ Runs a task on a remote host. """
    raise NotImplementedError


main = typer.Typer()
main.command(name='version')(commands_version)
main.command(name='root')(command_root)
main.command(name='init')(command_init)
main.command(name='generate')(command_generate)
main.command(name='open')(command_open)
main.command(name='export')(command_export)
main.command(name='remote')(command_remote)

if __name__ == '__main__':
    main()
