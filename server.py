import socket
import threading
import time
from datetime import datetime

class BattleshipServer:
    def __init__(self):
        self.clients = []
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def send_msg(self, conn, msg):
        try:
            if isinstance(msg, str): msg = msg.encode()
            conn.sendall(msg + b'\n')
        except: pass

    def broadcast(self, message, exclude_conn=None):
        with self.lock:
            for conn in self.clients:
                if conn != exclude_conn:
                    self.send_msg(conn, message)

    def handle_client(self, conn, addr):
        self.log(f"[+] NEW PLAYER: {addr}")
        buffer = ""
        while True:
            try:
                data = conn.recv(1024)
                if not data: break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    if not message: continue
                    if message == "QUIT": raise Exception("Client Quit")
                    self.broadcast(message, exclude_conn=conn)
            except: break

        with self.lock:
            if conn in self.clients: self.clients.remove(conn)
        conn.close()
        self.log(f"[-] DISCONNECT: {addr}")
        self.broadcast("OPPONENT_LEFT")

    def start(self):
        try:
            self.server.bind(('0.0.0.0', 65432))
            self.server.listen(5)
            print("="*40); print(" BATTLESHIP SERVER V3 (TURN FIXED)"); print("="*40)

            while True:
                conn, addr = self.server.accept()
                with self.lock:
                    if len(self.clients) < 2:
                        self.clients.append(conn)
                        threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
                        
                        if len(self.clients) == 1:
                            self.send_msg(conn, "WAIT")
                            self.log("Player 1 Connected. Waiting...")
                        elif len(self.clients) == 2:
                            self.log("Player 2 Joined. STARTING GAME!")
                            time.sleep(1)
                            # QUAN TRỌNG: Chỉ định ai đi trước
                            self.send_msg(self.clients[0], "START:1") # P1 đi trước
                            self.send_msg(self.clients[1], "START:2") # P2 đi sau
                    else:
                        self.send_msg(conn, "FULL"); conn.close()
        except KeyboardInterrupt: pass
        finally: self.server.close()

if __name__ == "__main__":
    BattleshipServer().start()

