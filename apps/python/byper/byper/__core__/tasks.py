import json
import os
import sys
import builtins
import importlib
from typing import TYPE_CHECKING

from byper.__core__.project_env import run_in_project, run_project_python, validate_project_environment

if TYPE_CHECKING:
    from byper.__core__.manifest import Manifest

Manifest = getattr(__import__("byper.__core__.manifest", fromlist=["Manifest"]), "Manifest")


class Tasks:
    @staticmethod
    def run_task(name: str):
        validate_project_environment()

        task_lines = Manifest.load_tasks_from_manifest(name)
        scripts = Manifest.load_requirements_manifest().get("scripts", {})

        if not task_lines:
            print(f"Task '{name}' not found.")
            return

        exec_scope = {
            "__builtins__": builtins.__dict__,
        }

        for i, line in enumerate(task_lines, 1):
            if isinstance(line, dict) and "call" in line:
                func_path = line["call"]
                raw_args = line.get("args", [])
                kwargs = line.get("kwargs", {})

                if isinstance(raw_args, dict):
                    kwargs = {**raw_args, **kwargs}
                    args = []
                else:
                    args = raw_args

                Tasks._call_function(func_path, args=args, kwargs=kwargs)

            elif isinstance(line, dict) and "file" in line:
                file_path = line["file"]
                Tasks._run_python_file(file_path)

            elif isinstance(line, str):
                line = line.strip()

                if line.startswith("byper run "):
                    script_name = line.split("byper run ", 1)[1].strip()
                    Tasks._run_script(script_name, scripts)

                elif line.startswith("byper "):
                    script_name = line.split("byper ", 1)[1].strip()
                    Tasks._run_script(script_name, scripts)

                else:
                    try:
                        print(f"> Executing task line: {line}")
                        exec(line, exec_scope)
                    except Exception as e:
                        print(f"[Line {i}] Error executing Python line: '{line}': {e}")

            elif isinstance(line, dict) and len(line) == 1:
                key, value = list(line.items())[0]
                combined = f"{key}: {value}" if not key.strip().endswith(":") else f"{key} {value}"
                try:
                    exec(combined, exec_scope)
                except Exception as e:
                    print(f"[Line {i}] Error executing composed line: '{combined}': {e}")

            else:
                print(f"[Line {i}] Unsupported task line format: {line}")

    @staticmethod
    def _run_script(script_name: str, scripts: dict):
        script_command = scripts.get(script_name)
        if script_command:
            print(f"> Running script '{script_name}': {script_command}")
            try:
                run_in_project(script_command, check=True)
            except Exception as e:
                print(f"Script execution failed: {e}")
        else:
            print(f"Script '{script_name}' not found.")

    @staticmethod
    def _run_python_file(file_path: str):
        if not os.path.exists(file_path):
            print(f"Python file '{file_path}' not found.")
            return
        print(f"> Running Python file: {file_path}")
        try:
            run_project_python([file_path], check=True)
        except Exception as e:
            print(f"Python file execution failed: {e}")

    @staticmethod
    def _call_function(func_path: str, args=None, kwargs=None):
        """Ejecuta una función del proyecto dentro del Python del environment local."""
        args = args or []
        kwargs = kwargs or {}

        args_json = json.dumps(args)
        kwargs_json = json.dumps(kwargs)

        code = f"""
import json, os, sys
sys.path.insert(0, {json.dumps(os.getcwd())})
args = json.loads({json.dumps(args_json)})
kwargs = json.loads({json.dumps(kwargs_json)})
module_name, func_name = {json.dumps(func_path)}.rsplit('.', 1)
module = __import__(module_name, fromlist=[func_name])
func = getattr(module, func_name)
print("> Calling function " + {json.dumps(func_path)})
func(*args, **kwargs)
"""
        try:
            run_project_python(["-c", code], check=True)
        except Exception as e:
            print(f"Failed to call function '{func_path}': {e}")
