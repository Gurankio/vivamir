import contextlib
import dataclasses
import functools
import pty
import re
import subprocess
from typing import Optional, List

from rich import print
from rich.console import Console

from vivamir.commands.generate import command_generate
from vivamir.vivamir import Vivamir


@dataclasses.dataclass()
class TaskReport:
    task: str
    cpu: str
    elapsed: str
    peak: str
    gain: str
    free_physical: str
    free_virtual: str

    @staticmethod
    @functools.lru_cache()
    def pattern():
        return re.compile(
            r'^(.+): Time \(s\): cpu = (.+?); elapsed = (.+?) \. Memory \(MB\): peak = (.+?) ; gain = (.+?) ; free physical = (.+?) ; free virtual = (.+?)$'
        )

    @classmethod
    def parse_if_match(cls, line: str) -> Optional['TaskReport']:
        if match := cls.pattern().match(line):
            return TaskReport(*match.groups())

    def __str__(self):
        return f'INFO: [vivamir::report] {self.task} in {self.elapsed}s'


@contextlib.contextmanager
def clean_vivado(vivamir: Vivamir, vivado_executable: List[str]):
    process = None
    try:
        _, fake_stdin = pty.openpty()
        process = subprocess.Popen(
            args=[
                *vivado_executable, '-mode', 'batch', '-source', 'open.tcl'
            ],
            cwd=vivamir.root / 'vivamir',
            stdin=fake_stdin,
            text=True,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print('INFO: [Vivamir] Vivado started.')
        yield process
    finally:
        if process is not None:
            try:
                print('\nINFO: [Vivamir] Awaiting Vivado termination.')
                stdout, stderr = process.communicate(timeout=15)
                if stdout is not None:
                    print(stdout)
                if stderr is not None:
                    print(stderr)

            except (KeyboardInterrupt, subprocess.TimeoutExpired):
                process.kill()
                print('INFO: [Vivamir] Vivado terminated forcefully.')
            else:
                print('INFO: [Vivamir] Vivado terminated.')


def command_open(vivado_executable: List[str]):
    """ Runs Vivado and opens the GUI with a fresh project. """

    vivamir = Vivamir.search()
    if vivamir is None:
        print('[bold red]No vivamir configuration found in the current working directory.')
        return 1

    print('INFO: [Vivamir] Regenerating scripts...')
    command_generate()

    console = Console()
    buffer = ''
    style = ''

    with clean_vivado(vivamir, vivado_executable) as process:
        while process.poll() is None:
            try:
                line = process.stdout.readline().rstrip()

                if task := TaskReport.parse_if_match(line):
                    console.print(str(task), style='dim')
                    continue

                if line.startswith('##'):
                    continue

                line = line.replace('# ', '', 1)
                buffer += line

                if line.startswith('INFO: '):
                    style = 'dim'

                if line.startswith('WARNING: '):
                    style = 'yellow'

                if line.startswith('CRITICAL WARNING: ') or line.startswith('ERROR: '):
                    style = 'bold red'

                if line.endswith(':'):
                    continue

                console.print(line, style=style, markup=False, highlight=False)
                buffer = ''
                style = ''

            except Exception as e:
                print(f'ERROR: Python crashed with {e!s}')
