import sys
from byper.env.__module__ import EnvModule


sys.modules[__name__] = EnvModule(__name__)

