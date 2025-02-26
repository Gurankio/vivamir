import dataclasses
import functools
import subprocess
import tomllib
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional

import dacite
from vivamir.utility.version import SemanticVersion


@functools.total_ordering
class ProjectPath(Path):
    """ New type wrapper to handle files relative to the project root. """

    def sort_key(self) -> tuple:
        return (
            tuple(map(lambda p: p.name, reversed(self.parents)))[1:],
            len(self.parents),
            len(self.suffixes),
            self.name.count('*'),
            self.name
        )

    def __lt__(self, other):
        """ Sorts paths in a visually pleasing manner. """
        if not isinstance(other, ProjectPath):
            return super().__lt__(other)

        return self.sort_key() < other.sort_key()

    def exists(self, *, follow_symlinks=True):
        raise ValueError('Cannot call exists on ProjectPath instance, use exists_in_project(root) instead.')

    def exists_in_project(self, vivamir: 'Vivamir', *, follow_symlinks=True):
        return (vivamir.root / self).exists()


@dataclasses.dataclass(slots=True)
class Include:
    path: ProjectPath = dataclasses.field(default=None)
    exec: str = dataclasses.field(default=None)

    def resolve(self, root: Path):
        if self.path is None:
            if self.exec is None:
                raise ValueError("Either path or exec must be specified.")

            output = Path(
                subprocess.run(
                    self.exec,
                    check=True, capture_output=True, text=True,
                    cwd=root, shell=True,
                ).stdout.strip()
            )
            self.path = ProjectPath(output.resolve(strict=True).relative_to(root))


class FilesetKind(Enum):
    DES = 'design'
    SIM = 'simulation'

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


@dataclasses.dataclass(slots=True)
class Fileset:
    kind: FilesetKind
    path: ProjectPath = dataclasses.field(default=None)
    exec: str = dataclasses.field(default=None)
    read_only: bool = dataclasses.field(default=False)

    def resolve(self, root: Path):
        if self.path is None:
            if self.exec is None:
                raise ValueError("Either path or exec must be specified.")

            output = Path(
                subprocess.run(
                    self.exec,
                    check=True, capture_output=True, text=True,
                    cwd=root, shell=True,
                ).stdout.strip()
            )
            self.path = ProjectPath(output.resolve(strict=True).relative_to(root))


@dataclasses.dataclass(slots=True)
class Ignore:
    include: Optional[ProjectPath]
    list: Optional[set[ProjectPath]]


@dataclasses.dataclass(slots=True)
class BlockDesigns:
    new_design_path: ProjectPath
    trusted: list[ProjectPath]


@dataclasses.dataclass(slots=True)
class IPs:
    user_ip_repo_path: ProjectPath


class SshRemote:
    host: str
    vivado: Path


@dataclasses.dataclass(slots=True)
class Remote:
    ssh: Optional[list[SshRemote]]


@dataclasses.dataclass(slots=True)
class VivadoProperty:
    name: str
    value: str
    object: str

    def as_tcl(self) -> str:
        return f'set_property -name {self.name} -value {self.value} -object {self.object}'


@dataclasses.dataclass(slots=True)
class Vivado:
    version: str
    part: str
    board: str
    board_long: str
    properties: Optional[list[VivadoProperty]]


@dataclasses.dataclass(slots=True)
class Vivamir:
    root: Path = dataclasses.field(init=False)
    version: SemanticVersion
    name: str
    ignore: Optional[Ignore]
    design_top: str
    simulation_top: str
    filesets: list[Fileset]
    includes: list[Include]
    block_designs: BlockDesigns
    ips: IPs
    remotes: Remote
    vivado: Vivado

    def first_fileset(self, kind: FilesetKind) -> Optional[Fileset]:
        return next(f for f in self.filesets if f.kind == kind)

    @classmethod
    def load(cls, root: Path) -> 'Vivamir':
        def _resolve_relative(path: Path) -> Optional[ProjectPath]:
            return ProjectPath((root / path).resolve().relative_to(root))

        self = dacite.from_dict(
            cls, tomllib.loads((root / 'vivamir.toml').read_text(), parse_float=Decimal),
            dacite.Config(
                strict=True, cast=[
                    float, set, Enum, Path,
                    # Allow simple string to be parsed as project paths.
                    # Include
                ],
                type_hooks={ProjectPath: _resolve_relative}),
        )

        if not SemanticVersion.project().compatible(self.version):
            raise ValueError('Incompatible configuration.')

        self.root = root

        if not ((self.ignore.include is None) ^ (self.ignore.list is None)):
            raise ValueError('Either ignore include or list must be specified.')

        if self.ignore.include is not None:
            include = (root / self.ignore.include).resolve(strict=True)
            self.ignore.list = set(_resolve_relative(Path(line)) for line in include.read_text().splitlines()
                                   if len(line) > 0 and not line.startswith('#'))

        for fileset in self.filesets:
            fileset.resolve(root)

        if self.includes is None:
            self.includes = []

        for include in self.includes:
            include.resolve(root)

        for bd in self.block_designs.trusted:
            if bd.suffix != '.tcl':
                raise ValueError("Block designs must have '.tcl' suffix")

        if self.remotes.ssh is None:
            self.remotes.ssh = []

        return self

    @classmethod
    def search(cls) -> Optional['Vivamir']:
        root = Path.cwd()
        while not (root / 'vivamir.toml').exists():
            if root.parent == root:
                return None
            else:
                root = root.parent
        return cls.load(root)
