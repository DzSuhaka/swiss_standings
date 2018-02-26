import socket
import time
import json
from threading import *

def recvall(sock, buffer_size=4096):
    buf = sock.recv(buffer_size)
    while buf:
        yield buf
        if not buf: break
        buf = sock.recv(buffer_size)

class HexApiListener():

    s = socket.socket()
    host = 'localhost'
    port = 1337
    s.bind((host,port))
    s.listen(5)

    def __init__(self):

        import sample  # TODO: clear this shit
        self.last_tournament_msg = sample.msg
        self.new_m = False
        self._start_listening()

    def start_listening(self):
        self.l = True

        while self.l:
            c, addr = self.s.accept()         
            temp_msg = ''.join(recvall(c, buffer_size = 4096))
            try:
                msg = json.loads(temp_msg.split('\r\n')[-2])
            except:
                msg = {}

            if msg:
                if len(msg['TournamentData']['Games']) > 3:
                    if self.last_tournament_msg != msg['TournamentData']:
                        self.last_tournament_msg = msg['TournamentData']
                        self.new_m = True
                    else:
                        self.new_m = False

            c.close()

    def _start_listening(self):
        self.thread = Thread(target=self.start_listening)
        self.thread.start()

    def _stop_listening(self):

        self.l = False

        sock = socket.socket()
        sock.connect((self.host, self.port))
        sock.send('die hard :<')
        sock.close()

        self.thread.join()
