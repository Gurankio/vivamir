import re
import shutil
from pathlib import Path
from typing import Optional

from rich import print

from vivamir.vivamir import Vivamir
from vivamir.utility.paths import DEFAULT
from vivamir.utility.version import SemanticVersion
from vivamir.utility.prompt import prompt_until_valid

_VERSION_PATTERN = re.compile(r'^(\d+)\.(\d+)$')


def _validate_name(name: str) -> Optional[str]:
    if ' ' in name:
        print('[bold red]Project name cannot contain spaces.')
        return None

    return name


def _validate_version(version: str) -> Optional[str]:
    if not _VERSION_PATTERN.fullmatch(version):
        print(f'[bold red]Version does not match: {_VERSION_PATTERN}')
        return None

    return version


def _validate_part(part: str) -> Optional[str]:
    print('[yellow]No validation has been implemented yet.')
    return part


def _validate_board(board: str) -> Optional[str]:
    print('[yellow]No validation has been implemented yet.')
    return board


def _validate_board_long(board_long: str) -> Optional[str]:
    print('[yellow]No validation has been implemented yet.')
    return board_long


def command_init():
    """ Initialise a new Vivamir project. """

    if Vivamir.search() is not None:
        print('[bold red]Project found, aborting.')
        return

    project = Path.cwd()

    name = prompt_until_valid('Base library name', _validate_name, project.name)
    version = prompt_until_valid('Vivado version', _validate_version, '2022.2')
    part = prompt_until_valid('Vivado part', _validate_part)
    board = prompt_until_valid('Vivado board', _validate_board)
    board_long = prompt_until_valid('Vivado board long', _validate_board_long)

    current_version = SemanticVersion.project()
    config = ((DEFAULT / 'vivamir.pyl')
              .read_text()
              .format(name=name, version=version, part=part, board=board, board_long=board_long,
                      major=current_version.major, minor=current_version.minor, patch=current_version.patch))
    (project / 'vivamir.toml').write_text(config)

    # Copy defaults ignoring "Python Literals".
    shutil.copytree(DEFAULT, project, ignore=shutil.ignore_patterns('*.pyl'), dirs_exist_ok=True)

    vivamir = Vivamir.load(project)
    for fileset in vivamir.filesets:
        fileset.path.mkdir(parents=True, exist_ok=True)

    print('Created `vivamir.toml` and `vivamir.ignore` files.')
    print('[green]Done!')
