import subprocess
from time import sleep
from typing import Iterator

import sys
from rich import print

from vivamir.commands.generate import command_generate
from vivamir.vivamir import Vivamir


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
    tail = None

    try:
        logfile = vivamir.root / 'vivamir' / 'vivado.log'
        logfile.unlink(missing_ok=True)
        # logfile.touch()

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

        while process.poll() and not logfile.exists():
            sleep(0.100)

        if process.poll():
            tail = subprocess.Popen(
                args=['tail', '-n50', '-f', str(logfile.resolve())],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

        while process.poll() is None:
            sleep(0.250)

    finally:
        if tail is not None:
            tail.kill()

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
