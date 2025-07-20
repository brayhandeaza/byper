import asyncio
import multiprocessing
import threading
import time
import socket
import inspect
from byper.States.__module__.backend import LocalBackend
from byper.States.__module__.ipc import IPCBackend, IPCServer
from typing import Callable, Dict, List, Any
from functools import wraps


_watchers: Dict[str, List[Callable]] = {}
_watchers_lock = threading.Lock()


class Manager:
    _instance = None
    _server_process = None
    _IPC_ADDRESS = ('localhost', 0)
    _AUTHKEY = b'viper_ipc_auth'

    def __init__(self):
        self._states = {}
        self._use_ipc = self._is_port_open(*self._IPC_ADDRESS)

        if self._use_ipc:
            self._backend = IPCBackend()
        else:
            self._backend = LocalBackend()

    def _is_port_open(self, host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(0.1)
                s.connect((host, port))
                return True
            except Exception:
                return False

    def _trigger_watchers(self, key: str, value: Any):
        with _watchers_lock:
            watchers = _watchers.get(key, []).copy()
            for fn in watchers:
                if inspect.iscoroutinefunction(fn):
                    asyncio.create_task(fn(value))
                else:
                    fn(value)

    def __call__(self, *args, **kwds):
        if self._instance is None:
            self._ensure_server()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Manager()
            cls._instance._ensure_server()
        return cls._instance

    def _ensure_server(self):
        # If IPC not used, no server needed
        if not self._use_ipc:
            return

        if not Manager._server_process or not Manager._server_process.is_alive():
            server = IPCServer(address=self._IPC_ADDRESS, authkey=self._AUTHKEY)

            Manager._server_process = multiprocessing.Process(target=server.start, daemon=True)
            Manager._server_process.start()

            # Wait briefly for server to come up
            time.sleep(0.2)

    def set(self, key, value):
        self._backend.set(key, value)

        self._trigger_watchers(key, value)

    def watch(self, key: str):
        def decorator(fn: Callable):
            @wraps(fn)
            def safe_wrapper(*args, **kwargs):
                try:
                    return fn()  # Try calling with no args
                except TypeError:
                    try:
                        return fn(*args, **kwargs)  # Try calling with whatever args were passed
                    except TypeError:
                        return  # Ignore if still not callable

            with _watchers_lock:
                if key not in _watchers:
                    _watchers[key] = []
                if safe_wrapper not in _watchers[key]:
                    _watchers[key].append(safe_wrapper)

            return safe_wrapper
        return decorator

    def get(self, key):
        value = self._backend.get(key)

        if key not in self._states:
            self._states[key] = value
        return value
