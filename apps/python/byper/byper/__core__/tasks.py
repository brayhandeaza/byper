import os
import sys
import subprocess
import builtins
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from byper.__core__.manifest import Manifest

Manifest = getattr(importlib.import_module("byper.__core__.manifest"), "Manifest")


class Tasks:
    @staticmethod
    def run_task(name: str):
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
                # Function call with args/kwargs
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
                # Run external Python file
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
                # Special case like: { 'with open(...) as f': 'f.write(...)' }
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
                subprocess.run(script_command, shell=True, check=True)
            except subprocess.CalledProcessError as e:
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
            subprocess.run(["python", file_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Python file execution failed: {e}")

    @staticmethod
    def _call_function(func_path: str, args=None, kwargs=None):
        """
        Import and call a Python function by full path like 'mymodule.myfunc',
        supporting optional positional and keyword arguments.
        """
        try:
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.insert(0, cwd)

            module_name, func_name = func_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            print(f"> Calling function {func_path}({args or ''}{', ' if args and kwargs else ''}{kwargs or ''})")
            func(*(args or []), **(kwargs or {}))
        except Exception as e:
            print(f"Failed to call function '{func_path}': {e}")
