import threading


class LocalBackend:
    def __init__(self):
        self._state = {}
        self._subscriptions = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            return self._state.get(key)

    def set(self, key, value):
        with self._lock:
            self._state[key] = value
            for cb in self._subscriptions.get(key, []):
                try:
                    cb(value)
                except Exception:
                    pass

    def subscribe(self, key, callback):
        with self._lock:
            self._subscriptions.setdefault(key, []).append(callback)
