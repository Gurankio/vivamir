import dataclasses
import functools
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, List, Set

import dacite
import toml

from vivamir.utility.version import SemanticVersion


@functools.total_ordering
@dataclasses.dataclass()
class ProjectPath:
    """ New type wrapper to handle files relative to the project root. """
    path: Path

    def __getattr__(self, item):
        return getattr(self.path, item)

    def __truediv__(self, key):
        return ProjectPath(self.path.__truediv__(key))

    def __rtruediv__(self, key):
        return ProjectPath(self.path.__rtruediv__(key))

    def __hash__(self):
        return hash(str(self.path.resolve()))

    def __repr__(self):
        return repr(self.path)

    def __str__(self):
        return str(self.path)

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
        return (vivamir.root / self.path).exists()


@dataclasses.dataclass()
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


@dataclasses.dataclass()
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


@dataclasses.dataclass()
class Ignore:
    include: Optional[ProjectPath]
    list: Optional[Set[ProjectPath]]


@dataclasses.dataclass()
class BlockDesigns:
    new_design_path: ProjectPath
    trusted: List[ProjectPath]


@dataclasses.dataclass()
class IPs:
    user_ip_repo_path: ProjectPath


class SshRemote:
    host: str
    vivado: Path


@dataclasses.dataclass()
class Remote:
    ssh: Optional[List[SshRemote]]


@dataclasses.dataclass()
class VivadoProperty:
    name: str
    value: str
    object: str

    def as_tcl(self) -> str:
        return f'set_property -name {self.name} -value {self.value} -object {self.object}'


@dataclasses.dataclass()
class Vivado:
    version: str
    part: str
    board: str
    board_long: str
    properties: Optional[List[VivadoProperty]]


@dataclasses.dataclass()
class Vivamir:
    root: Path = dataclasses.field(init=False)
    version: SemanticVersion
    name: str
    ignore: Optional[Ignore]
    design_top: str
    simulation_top: str
    filesets: List[Fileset]
    includes: List[Include]
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
            cls, toml.loads((root / 'vivamir.toml').read_text()),
            dacite.Config(
                strict=True, cast=[
                    float, set, Enum, Path,
                    # Allow simple string to be parsed as project paths.
                    # Include
                ],
                check_types=False,
                type_hooks={
                    ProjectPath: _resolve_relative
                }),
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
