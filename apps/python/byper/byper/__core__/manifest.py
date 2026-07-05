import json
import os
import subprocess
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from byper.__core__.constants import REQUIREMENTS_FILE
from byper.__core__.project_env import run_project_pip

if TYPE_CHECKING:
    from byper.__core__.utils.logger import Logger

Logger = getattr(__import__("byper.__core__.utils.logger", fromlist=["Logger"]), "Logger")


class Manifest:
    @staticmethod
    def save_manifest(data: dict):
        name = data.pop("name", None)
        description = data.pop("description", None)
        version = data.pop("version", None)
        entry = data.pop("entry", None)
        author = data.pop("author", None)
        license = data.pop("license", None)
        python = data.pop("python", None)

        scripts = data.pop("scripts", None)
        aliases = data.pop("aliases", None)
        tasks = data.pop("tasks", None)
        env = data.pop("env", None)
        dependencies = data.pop("dependencies", None)

        if aliases:
            Logger.log(
                "Warning: `aliases` is no longer supported by Byper and will be ignored.",
                level="warn",
            )

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        header_fields = [
            ("name", name),
            ("description", description),
            ("version", version),
            ("entry", entry),
            ("author", author),
            ("license", license),
        ]

        sections = [
            ("scripts", scripts),
            ("tasks", tasks),
            ("env", env),
            ("dependencies", dependencies),
        ]

        with open(REQUIREMENTS_FILE, "w") as f:
            for key, value in header_fields:
                if not value:
                    continue
                yaml.dump({key: value}, f)

            if python:
                f.write("\n")
                yaml.dump({"python": python}, f)

            for key, value in sections:
                if not value:
                    continue
                f.write("\n")
                yaml.dump({key: value}, f)

            for key, value in data.items():
                if not value:
                    continue
                f.write("\n")
                yaml.dump({key: value}, f)

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
                "python": None,
                "scripts": {},
                "tasks": {},
                "env": {},
                "dependencies": {},
            }

        yaml = YAML()
        with open(REQUIREMENTS_FILE, "r") as f:
            data = yaml.load(f) or {}

        if "aliases" in data:
            Logger.log(
                "Warning: `aliases` is no longer supported by Byper and will be ignored.",
                level="warn",
            )

        return {
            "name": data.get("name"),
            "description": data.get("description"),
            "version": data.get("version"),
            "entry": data.get("entry"),
            "license": data.get("license"),
            "author": data.get("author"),
            "python": data.get("python"),

            "scripts": dict(data.get("scripts", {}) or {}),
            "tasks": dict(data.get("tasks", {}) or {}),
            "dependencies": dict(data.get("dependencies", {}) or {}),
            "env": dict(data.get("env", {}) or {}),
        }

    @staticmethod
    def load_installed_manifest():
        Logger.log("↪ Scanning installed packages from environment", indent=1)

        try:
            result = run_project_pip(
                ["list", "--format=json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
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
