from typing import Any, Dict, Union
import sys
import importlib
import inspect
import os
from dotenv import dotenv_values, load_dotenv
import yaml
from pathlib import Path
from typing import TYPE_CHECKING
from byper.__core__.constants import REQUIREMENTS_FILE
from types import ModuleType

if TYPE_CHECKING:
    from byper.__core__.manifest import Manifest
    from byper.__core__.environment import Environment

Manifest = getattr(importlib.import_module("byper.__core__.manifest"), "Manifest")
Environment = getattr(importlib.import_module("byper.__core__.environment"), "Environment")


_last_checked = 0
_aliases_cache = {}


def load_aliases():
    global _last_checked, _aliases_cache
    if not os.path.exists(REQUIREMENTS_FILE):
        return {}

    mtime = os.path.getmtime(REQUIREMENTS_FILE)
    if mtime > _last_checked:
        _last_checked = mtime
        with open(REQUIREMENTS_FILE, "r") as f:
            config = yaml.safe_load(f) or {}
            _aliases_cache = config.get("aliases", {})
    return _aliases_cache


def generate_aliases_pyi():
    base_path = Path(os.getcwd()).resolve()
    aliases = load_aliases()

    if not aliases:
        return

    lines = [
        "# Auto-generated alias stubs by Byper for IDE support",
        "from types import ModuleType",
        "from typing import Any, Callable",
        "",
    ]

    # add base_path route to sys.path
    sys.path.insert(0, str(base_path))
    for alias, target_path in aliases.items():
        try:
            parts = target_path.split(".")
            if len(parts) == 1:
                obj = importlib.import_module(target_path)
            else:
                mod = importlib.import_module(".".join(parts[:-1]))
                obj = getattr(mod, parts[-1])

            # Class stub
            if inspect.isclass(obj):
                lines.append(f"class {alias}(ModuleType):")
                for name, member in inspect.getmembers(obj):
                    if name.startswith("_"):
                        continue
                    if inspect.isfunction(member) or inspect.ismethod(member):
                        try:
                            sig = inspect.signature(member)
                            lines.append(f"    def {name}{sig} -> Any: ...")
                        except Exception:
                            lines.append(f"    def {name}(*args, **kwargs) -> Any: ...")
                    elif isinstance(member, property):
                        lines.append(f"    @property")
                        lines.append(f"    def {name}(self) -> Any: ...")
                    else:
                        lines.append(f"    {name}: Any")
                lines.append("")

            # Function stub
            elif inspect.isfunction(obj):
                try:
                    sig = inspect.signature(obj)
                    lines.append(f"def {alias}{sig} -> Any: ...")
                except Exception:
                    lines.append(f"def {alias}(*args, **kwargs) -> Any: ...")
                lines.append("")

            # Module stub
            elif isinstance(obj, ModuleType):
                lines.append(f"class {alias}(ModuleType):")
                for name, member in inspect.getmembers(obj):
                    if name.startswith("_"):
                        continue
                    if inspect.isfunction(member):
                        try:
                            sig = inspect.signature(member)
                            lines.append(f"    def {name}{sig} -> Any: ...")
                        except Exception:
                            lines.append(f"    def {name}(*args, **kwargs) -> Any: ...")
                    elif inspect.isclass(member):
                        lines.append(f"    class {name}: ...")
                    else:
                        lines.append(f"    {name}: Any")
                lines.append("")

            # Variable/constant stub
            else:
                lines.append(f"{alias}: Any")
                lines.append("")

        except Exception as e:
            lines.append(f"# Failed to generate stub for alias {alias}: {e}")
            lines.append(f"{alias}: Any")
            lines.append("")

    # Write __init__.pyi
    path = base_path / Environment.get_install_dir() / "byper/aliases/"
    pyi_path = os.path.join(path, "__init__.pyi")

    os.makedirs(path, exist_ok=True)

    with open(pyi_path, "w") as f:
        f.write("\n".join(lines))


def generate_tasks_stub():
    path = Path(os.getcwd()).resolve() / Environment.get_install_dir() / "byper/tasks/"

    stub_path = os.path.join(path, "__init__.pyi")
    manifest = Manifest.load_requirements_manifest()
    tasks = manifest.get("tasks", {})

    lines = [
        f"def {task_name}() -> None: ..."
        for task_name in tasks
        if task_name.isidentifier()
    ]

    content = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(stub_path), exist_ok=True)

    try:
        with open(stub_path, "w") as f:
            f.write(content)
    except Exception as e:
        # Optional: silently ignore or log error
        print(f"[Warning] Failed to write stub file: {e}")


def load_env_file(file_path: Union[str, Path]) -> Dict[str, str]:
    """Loads a .env file using python-dotenv and returns key-value pairs."""
    path = Path(file_path).resolve()

    # Load into os.environ (side-effect)
    load_dotenv(dotenv_path=path, override=True)

    # Return dict (for __init__.pyi generation)
    return {k: str(v) for k, v in dotenv_values(path).items() if k}


def load_env_from_manifest() -> Dict[str, Any]:
    """Loads env variables from Requirements.yml, supports 'from_file' and inline overrides."""
    data: Dict[str, Any] = {}
    manifest = Manifest.load_requirements_manifest()
    env_config = manifest.get("env", {})

    if not isinstance(env_config, dict):
        return data

    # 1. Load from `from_file` first
    file_key = env_config.get("from_file")
    if isinstance(file_key, str):
        file_path = Path(file_key).resolve()
        if file_path.exists() and file_path.is_file():
            file_data = load_env_file(file_path)
            data.update(file_data)  # Add all .env values

    # 2. Load inline values (override file)
    for key, value in env_config.items():
        if key == "from_file":
            continue  # already handled

        os.environ[key] = str(value)
        data[key] = str(value)

    return data


def generate_env_stub():
    """Generates a __init__.pyi stub file with env variables."""
    lines = [
        "# Auto-generated by Byper for IDE support",
        "from typing import Any",
        "",
    ]
    env_data = load_env_from_manifest()
    for key in sorted(env_data):
        if key.isidentifier():
            lines.append(f"{key}: Any")

        else:
            lines.append(f"# Invalid Python identifier: {key}")

    base_path = Path(os.getcwd()).resolve()
    path = base_path / Environment.get_install_dir() / "byper/env/"
    pyi_path = os.path.join(path, "__init__.pyi")

    os.makedirs(path, exist_ok=True)

    with open(pyi_path, "w") as f:
        f.write("\n".join(lines))
