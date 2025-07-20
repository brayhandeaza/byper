import os
from types import ModuleType
from byper.__core__.helpers import generate_env_stub, load_env_from_manifest


class EnvModule(ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.env_data = {}
        self._load_all()
        self._generate_stub()

    def _load_all(self):
        self.env_data = load_env_from_manifest()

        for key, val in self.env_data.items():
            os.environ[key] = val
            setattr(self, key, val)

    def _generate_stub(self):
        generate_env_stub()

    def reload(self):
        self.env_data.clear()
        self._load_all()
        self._generate_stub()
