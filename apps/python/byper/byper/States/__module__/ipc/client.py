import threading
from multiprocessing.connection import Client
import traceback


class IPCClient:
    def __init__(self, address=('localhost', 0), authkey=b'viper'):
        self.address = address
        self.authkey = authkey
        self.conn = None
        self.listeners = []
        self.lock = threading.Lock()
        self._connected = False

    def connect(self):
        if not self._connected:
            try:
                self.conn = Client(self.address, authkey=self.authkey)
                self._connected = True
                threading.Thread(target=self._listen, daemon=True).start()
            except Exception:
                traceback.print_exc()
                self._connected = False

    def _listen(self):
        while self._connected:
            try:
                msg = self.conn.recv()
                with self.lock:
                    for callback in self.listeners:
                        try:
                            callback(msg)
                        except Exception:
                            traceback.print_exc()
            except EOFError:
                break
            except Exception:
                traceback.print_exc()
                break
        self._connected = False

    def send(self, message):
        self.connect()
        self.conn.send(message)
        return self.conn.recv()

    def add_listener(self, callback):
        with self.lock:
            self.listeners.append(callback)

    def close(self):
        if self._connected:
            try:
                self.conn.send({'cmd': 'close'})
            except Exception:
                pass
            try:
                self.conn.close()
            except Exception:
                pass
            self._connected = False
