import importlib
import json
import os
import subprocess
from typing import TYPE_CHECKING
from byper.__core__.constants import REQUIREMENTS_FILE
from ruamel.yaml import YAML


if TYPE_CHECKING:
    from byper.__core__.environment import Environment
    from byper.__core__.utils.logger import Logger


Logger = getattr(importlib.import_module("byper.__core__.utils.logger"), "Logger")
Environment = getattr(importlib.import_module("byper.__core__.environment"), "Environment")


class Manifest:
    @staticmethod
    def save_manifest(data: dict):
        name = data.pop("name", None)
        version = data.pop("version", None)
        entry = data.pop("entry", None)
        license = data.pop("license", None)

        scripts = data.pop("scripts", None)
        aliases = data.pop("aliases", None)
        tasks = data.pop("tasks", None)
        dependencies = data.pop("dependencies", None)

        manifest = {
            "name": name,
            "version": version,
            "entry": entry,
            "license": license,

            "scripts": scripts,
            "aliases": aliases,
            "tasks": tasks,
            "dependencies": dependencies,
            **data,
        }

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        with open(REQUIREMENTS_FILE, "w") as f:
            for key, value in manifest.items():
                if not value:
                    continue

                if key in ["scripts", "aliases", "tasks", "dependencies"]:
                    f.write("\n")

                yaml.dump({key: value}, f)

                # if key in ["name", "version", "entry", "license"]:
                #     yaml.dump({key: value}, f)
                #     f.write("\n")

                # else:
                #     yaml.dump({key: value}, f)
                #     if value:
                #         f.write("\n")

    @staticmethod
    def load_requirements_manifest():
        if not os.path.exists(REQUIREMENTS_FILE):
            return {
                "name": None,
                "description": None,
                "version": None,
                "entry": None,
                "license": None,
                "author": None,
                "scripts": {},
                "aliases": {},
                "tasks": {},
                "env": {},
                "dependencies": {},
            }

        yaml = YAML()
        with open(REQUIREMENTS_FILE, "r") as f:
            data = yaml.load(f) or {}

        return {
            "name": data.get("name"),
            "description": data.get("description"),
            "version": data.get("version"),
            "entry": data.get("entry"),
            "license": data.get("license"),
            "author": data.get("author"),

            "scripts": dict(data.get("scripts", {}) or {}),
            "aliases": dict(data.get("aliases", {}) or {}),
            "tasks": dict(data.get("tasks", {}) or {}),
            "dependencies": dict(data.get("dependencies", {}) or {}),
            "env": dict(data.get("env", {}) or {}),
        }

    @staticmethod
    def load_installed_manifest():
        env_python = Environment.get_env_python()

        Logger.log("↪ Scanning installed packages from environment", indent=1)

        try:
            result = subprocess.run(
                [env_python, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True,
            )
            packages = json.loads(result.stdout)

        except Exception as e:
            Logger.log(
                f"❌ Failed to list packages from environment: {e}",
                level="error",
                indent=2,
            )
            return {}

        installed = {}

        for pkg in packages:
            name = pkg["name"].lower().replace("-", "_")
            version = pkg["version"]
            installed[name] = version
            Logger.log(f"↪ {name}=={version} is installed", level="command", indent=2)

        return installed

    @staticmethod
    def load_script_from_manifest(_script: str):
        if not os.path.exists(REQUIREMENTS_FILE):
            return {}

        yaml = YAML()
        with open(REQUIREMENTS_FILE, "r") as f:
            data = yaml.load(f) or {}

        scripts: dict = data.get("scripts", {})
        return scripts.get(_script)

    @staticmethod
    def load_tasks_from_manifest(task: str):
        if not os.path.exists(REQUIREMENTS_FILE):
            return {}

        yaml = YAML()
        with open(REQUIREMENTS_FILE, "r") as f:
            data = yaml.load(f) or {}

        tasks: dict = dict(data.get("tasks", {}) or {})
        return tasks.get(task)
