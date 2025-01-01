import unittest
from vivamir.utility.paths import DEFAULT
import tomllib
from tempfile import mkdtemp
from pathlib import Path

from vivamir.utility.version import SemanticVersion
from vivamir.vivamir import Vivamir


class TestParsing(unittest.TestCase):
    class AnyKey:
        def __getitem__(self, item):
            if item in ['major', 'minor', 'patch']:
                return SemanticVersion.project().__getattribute__(item)
            return item

    def test_valid_toml(self):
        default = (DEFAULT / 'vivamir.pyl').read_text().format_map(self.AnyKey())
        tomllib.loads(default)

    def test_parse(self):
        tmp = Path(mkdtemp()).resolve()
        (tmp / 'vivamir.toml').write_text((DEFAULT / 'vivamir.pyl').read_text().format_map(self.AnyKey()))
        (tmp / 'vivamir.ignore').write_text((DEFAULT / 'vivamir.ignore').read_text())
        Vivamir.load(tmp)


if __name__ == '__main__':
    unittest.main()
