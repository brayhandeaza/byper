from byper.States.__module__.ipc.client import IPCClient
import threading


class IPCBackend:
    def __init__(self):
        self._client = IPCClient()
        self._client.connect()
        self._subscriptions = {}
        self._lock = threading.Lock()
        self._client.add_listener(self._on_message)

    def get(self, key):
        resp = self._client.send({'cmd': 'get', 'key': key})
        return resp.get('response')

    def set(self, key, value):
        self._client.send({'cmd': 'set', 'key': key, 'value': value})

    def subscribe(self, key, callback):
        with self._lock:
            self._subscriptions.setdefault(key, []).append(callback)

    def _on_message(self, msg):
        if msg.get('event') == 'update':
            key = msg.get('key')
            value = msg.get('value')
            with self._lock:
                callbacks = self._subscriptions.get(key, [])
            for cb in callbacks:
                try:
                    cb(value)
                except Exception:
                    pass
