import dataclasses


@dataclasses.dataclass()
class SemanticVersion:
    major: int
    minor: int
    patch: int

    def compatible(self, other: "SemanticVersion") -> bool:
        return self.major == other.major

    @classmethod
    def project(cls) -> "SemanticVersion":
        import importlib.metadata
        major, minor, patch = importlib.metadata.version('vivamir').split('.')
        return cls(major=int(major), minor=int(minor), patch=int(patch))

    def __str__(self):
        return f'{self.major}.{self.minor}.{self.patch}'
