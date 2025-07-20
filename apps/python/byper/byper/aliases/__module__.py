import importlib
from byper.__core__.constants import REQUIREMENTS_FILE
from byper.__core__.helpers import generate_aliases_pyi, load_aliases
from byper.__core__.utils.logger import Logger


class AliasModule:
    def __init__(self):
        generate_aliases_pyi()

    def __getattr__(self, name):
        if name.startswith("__"):
            return super().__getattribute__(name)

        aliases = load_aliases()

        if name not in aliases:
            msg = f"Alias '{name}' not defined in {REQUIREMENTS_FILE}"
            Logger.log(msg, level="debug")
            raise ImportError(msg)

        target_path = aliases[name]
        try:
            parts = target_path.split(".")
            if len(parts) == 1:
                obj = importlib.import_module(target_path)
            else:
                mod = importlib.import_module(".".join(parts[:-1]))
                obj = getattr(mod, parts[-1])
            setattr(self, name, obj)
            return obj
        except Exception as e:
            Logger.log(str(e), level="debug")
            raise ImportError(str(e))
