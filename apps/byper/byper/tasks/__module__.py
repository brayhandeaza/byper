import sys
import os
import types
from typing import TYPE_CHECKING
from byper.__core__.tasks import Tasks as _Tasks
from byper.__core__.helpers import generate_tasks_stub

if TYPE_CHECKING:
    from byper.__core__.manifest import Manifest

Manifest = getattr(sys.modules["byper.__core__.manifest"], "Manifest")


class TasksModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self._init_tasks()
        generate_tasks_stub()

    def _init_tasks(self):
        manifest = Manifest.load_requirements_manifest()
        tasks = manifest.get("tasks", {})

        for task_name in tasks:
            if task_name.isidentifier():
                setattr(self, task_name, self._make_task_runner(task_name))

        # Set __all__ for 'from byper.tasks import *'
        self.__all__ = [t for t in tasks if t.isidentifier()]

    def _make_task_runner(self, name):
        def runner():
            return _Tasks.run_task(name)
        runner.__name__ = name
        runner.__doc__ = f"Run the manifest task '{name}'."
        return runner
