import threading
import traceback
from multiprocessing.connection import Listener


class IPCServer:
    def __init__(self, address=('localhost', 0), authkey=b'viper'):
        self.address = address
        self.authkey = authkey
        self.state = {}
        self.clients = []
        self.lock = threading.Lock()
        self.listener = Listener(self.address, authkey=self.authkey)
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._accept_clients, daemon=True).start()

    def _accept_clients(self):
        while self._running:
            try:
                conn = self.listener.accept()
                self.clients.append(conn)
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except Exception:
                traceback.print_exc()

    def _handle_client(self, conn):
        while self._running:
            try:
                msg = conn.recv()
                cmd = msg.get('cmd')
                if cmd == 'get':
                    key = msg.get('key')
                    with self.lock:
                        value = self.state.get(key)
                    conn.send({'response': value})
                elif cmd == 'set':
                    key = msg.get('key')
                    value = msg.get('value')
                    with self.lock:
                        self.state[key] = value
                    self._broadcast({'event': 'update', 'key': key, 'value': value})
                    conn.send({'response': 'ok'})
                elif cmd == 'close':
                    conn.close()
                    break
            except EOFError:
                break
            except Exception:
                traceback.print_exc()
                break

        if conn in self.clients:
            self.clients.remove(conn)

    def _broadcast(self, message):
        for client in self.clients[:]:
            try:
                client.send(message)
            except Exception:
                self.clients.remove(client)

    def stop(self):
        self._running = False
        self.listener.close()
        for c in self.clients:
            try:
                c.close()
            except Exception:
                pass
