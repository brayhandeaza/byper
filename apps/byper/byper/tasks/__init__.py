import sys
from byper.tasks.__module__ import TasksModule

sys.modules[__name__] = TasksModule(__name__)
