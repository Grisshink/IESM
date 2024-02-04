import requests
import json
import websocket
import hashlib
import random
import time

from zlib import crc32
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36',
    "x-csrftoken": "a",
    "x-requested-with": "XMLHttpRequest",
    "referer": "https://scratch.mit.edu",
}

PROTOCOL_VERSION = bytes([1])

def to_bytes(value: int) -> bytes:
    out = []
    while value > 0:
        out.append(value & 0xFF)
        value >>= 8
    return bytes(reversed(out))

#def _login(username: str, password: str) -> str:
#    return 'Some cookie'

def login(username: str, password: str) -> str:
    data = json.dumps({
        "username": username,
        "password": password,
    })
    _headers = headers
    _headers["Cookie"] = "scratchcsrftoken=a;scratchlanguage=en;"

    res = requests.post(
        "https://scratch.mit.edu/login/",
        data=data,
        headers=_headers,
    )
    if 'scratchsessionsid' not in res.cookies: raise ValueError('No session id :(')

    return res.cookies['scratchsessionsid']

class WsClosedError(Exception): pass
class NoVarError(Exception): pass

class DummyWs:
    def connect(self, *args, **kwargs):
        _ = args, kwargs
        self.messages = ['{"method":"set","project_id":"123","name":"☁ cloud 1","value":"100"}\n',
                         '{"method":"set","project_id":"123","name":"☁ cloud 2","value":"100"}\n',
                         '{"method":"set","project_id":"123","name":"☁ cloud 3","value":"100"}\n',]
        #self.messages = []

    def close(self):
        pass

    def send(self, data: str):
        print(f'Sent: {data}')
        if json.loads(data)['method'] == 'set':
            self.messages.append(data)

    def recv(self) -> str:
        time.sleep(0.8)
        try:
            return random.choice(self.messages)
        except:
            return ''

class Connection:
    def __init__(self, 
                 project_id: int, 
                 username: str, 
                 session_id: str | None, 
                 room_name: str,
                 encoding: str,
                 connection_type: str) -> None:
        self.project_id = project_id
        self.username = username
        self.session_id = session_id
        self.known_vars: set[str] = set()
        self.room_name = room_name
        self.room_hash = hashlib.sha256(self.room_name.encode()).digest()
        self.encoding = encoding
        self.reconnect = False
        self.connection_type = connection_type
        self.connect()

    def connect(self):
        self.reconnect = True
        self.ws = websocket.WebSocket()

        if self.connection_type == 'Scratch':
            if self.session_id is None: return
            self.ws.connect(
                'wss://clouddata.scratch.mit.edu',
                cookie="scratchsessionsid=" + self.session_id + ";",
                origin="https://scratch.mit.edu",
                enable_multithread=True,
            )
        else:
            self.ws.connect(
                'wss://clouddata.turbowarp.org/',
                enable_multithread=True,
                header=["User-Agent: Grisshink/IESM proto-ver/{PROTOCOL_VERSION[0]}"]
            )

        self.send_packet({ "method": "handshake", "user": self.username, "project_id": self.project_id })
        self.reconnect = False

    def close(self):
        if self.ws is None: raise WsClosedError('Websocket already closed!')
        if len(self.known_vars) > 0: self.set_variable(f'{self.username} вышел'.encode(encoding=self.encoding))

        self.ws.close()
        self.ws = None

    def send_message(self, message: str):
        enc_message = f'{self.username}> {message.strip()}'.encode(encoding=self.encoding)
        self.set_variable(enc_message)

    def set_variable(self, value: bytes):
        if self.ws is None: raise WsClosedError('Websocket not initialised!')
        if self.connection_type == 'Scratch' and len(value) > 79: raise NameError('Message too long!')
        if len(self.known_vars) == 0: raise NoVarError('No known vars!')

        cipher = AES.new(self.room_hash, AES.MODE_CBC)

        enc = cipher.encrypt(pad(value, AES.block_size))
        iv = bytes(cipher.iv)
        blob = iv + enc
        hashval = crc32(blob).to_bytes(4)

        inp = int((PROTOCOL_VERSION + hashval + blob).hex(), 16)

        while self.reconnect: time.sleep(1)

        self.send_packet({
            "method": "set",
            "name": random.choice(list(self.known_vars)),
            "value": str(inp),
            "user": self.username,
            "project_id": str(self.project_id),
        })

    def send_packet(self, data):
        if self.ws is None: raise WsClosedError('Websocket not initialised!')
        if 'value' in data and self.connection_type == 'Scratch' and len(data['value']) > 256:
            raise ValueError(f'Length of payload too long: {len(data["value"])}/256')

        self.ws.send(json.dumps(data) + "\n")

    def add_cloud_var(self, name: str) -> bool:
        name = f'☁ {name}'
        if name in self.known_vars: return False

        self.known_vars.add(name)

        if len(self.known_vars) == 1: self.set_variable(f'{self.username} присоеденился'.encode(encoding=self.encoding))
        return True

    def recv(self) -> str | None:
        if self.ws is None: raise WsClosedError('Websocket not initialised')
        out = None

        try:
            r = self.ws.recv()
        except websocket.WebSocketConnectionClosedException:
            try:
                self.reconnect = True
                time.sleep(0.5)
                self.connect()
                r = self.ws.recv()
                out = 'Переподключение успешно\n'
            except:
                time.sleep(1)
                self.connect()
                r = self.ws.recv()
                out = 'Переподключение успешно\n'

        if not isinstance(r, str):
            print(f'Got binary: {r}')
            return out
        
        print(r)
        split_data = r.split('\n')
        if split_data[-1] == '': split_data.pop()
        print(split_data)
        for packet in split_data:
            data = json.loads(packet)

            if data['name'] not in self.known_vars:
                string = f'Discovered new cloud variable: {data["name"]}\n'
                if out is None: out = string
                else: out += string
                self.known_vars.add(data['name'])

                if len(self.known_vars) == 1: self.set_variable(f'{self.username} присоеденился'.encode(encoding=self.encoding))
            
            inp = to_bytes(int(data['value']))
            if len(inp) < 36: return out

            version = inp[0]
            if version != PROTOCOL_VERSION[0]: continue

            hashval = inp[1:5]
            blob = inp[5:]
            if hashval != crc32(blob).to_bytes(4): return out

            iv = blob[:16]
            data = blob[16:]

            cipher = AES.new(self.room_hash, AES.MODE_CBC, iv)
            try:
                dec = unpad(cipher.decrypt(data), AES.block_size).decode(encoding=self.encoding) + '\n'
                if out is None: out = dec
                else: out += dec

                print(f'Packet info:'
                      f'\n\tVersion: {version}'
                      f'\n\tChecksum: {hashval.hex()}'
                      f'\n\tIV: {iv.hex()}'
                      f'\n\tData: {data.hex()}')

            except ValueError:
                pass

        return out
