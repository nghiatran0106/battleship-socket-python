import socket, threading, os, sys, tty, termios, time

class BattleshipClient:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.reset_game_state()

    def reset_game_state(self):
        self.my_board = [[0]*10 for _ in range(10)]
        self.enemy_view = [['.']*10 for _ in range(10)]
        self.my_ships_list = [] 
        self.cursor = [0, 0]
        self.history = ["Waiting for game start..."]
        self.my_turn = False
        self.player_id = 0
        self.game_state = "CONNECTING"
        self.running = True
        self.used_scan_3x3 = False
        self.used_leak = False
        self.total_health = 0
        self.opponent_ready_replay = False

    def get_key(self):
        fd = sys.stdin.fileno(); old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd); ch = sys.stdin.read(1)
            if ch == '\x1b': ch += sys.stdin.read(2)
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch

    def draw_ui(self):
        os.system('clear')
        # Header Status
        status = "UNKNOWN"
        if self.game_state == "CONNECTING": status = "WAITING FOR OPPONENT..."
        elif self.game_state == "PLACING": status = "SETUP PHASE (Place your ships)"
        elif self.game_state == "PLAYING": status = "YOUR TURN" if self.my_turn else "ENEMY TURN"
        elif self.game_state == "GAME_OVER": status = "--- GAME ENDED ---"

        print(f" PLAYER {self.player_id} | {status} | HP: {self.total_health}/13")
        if self.game_state == "PLAYING":
            print(" [Arrows]: Move | [Enter]: Fire | [S]: 3x3 | [A/D/W]: Line Radar")
        print(" LEGEND: [S] Ship | [X] Destroyed | [O] Miss | [R] Radar")
        print("="*60)
        
        # Draw Boards
        print("      MY FLEET                    ENEMY ZONE")
        print("   0 1 2 3 4 5 6 7 8 9           0 1 2 3 4 5 6 7 8 9")
        for r in range(10):
            row1 = []
            for c in range(10):
                val = self.my_board[r][c]
                char = '~'
                if val == 1: char = 'S'
                elif val == 'H': char = 'X' # Destroyed
                elif val == 'M': char = 'O' # Miss
                if self.game_state=="PLACING" and self.cursor==[r,c]: char=f"[{char}]"
                else: char=f" {char} "
                row1.append(char)
            row2 = []
            for c in range(10):
                val = self.enemy_view[r][c]
                char = val
                if self.game_state=="PLAYING" and self.cursor==[r,c]: char=f"[{char}]"
                else: char=f" {char} "
                row2.append(char)
            print(f"{r} |{''.join(row1)}|       {r} |{''.join(row2)}|")
        print("="*60)
        # Show more logs
        for log in self.history[-5:]: print(f" > {log}")

    def send_command(self, cmd):
        try: self.client.sendall(cmd.encode() + b'\n')
        except: pass

    def handle_network(self):
        buffer = ""
        while self.running:
            try:
                data = self.client.recv(1024)
                if not data: break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    if not message: continue
                    self.process_message(message)
            except: break
        self.running = False

    def process_message(self, message):
        if message == "OPPONENT_LEFT":
            self.history.append("Opponent Quit. Game Over.")
            self.game_state = "GAME_OVER"
            self.running = False
        
        elif message == "WAIT": self.history.append("Connected. Waiting P2...")
        
        elif message.startswith("START"):
            try:
                pid = int(message.split(':')[1])
                self.player_id = pid
                self.my_turn = True if pid == 1 else False
                self.history.append(f"MATCH FOUND! You are P{pid}.")
                self.game_state = "PLACING"
            except: pass

        elif message == "CMD:REPLAY":
            self.opponent_ready_replay = True
            self.history.append("Opponent wants to play again!")

        elif message.startswith("ACT:"):
            parts = message.split(':')[1].split(',')
            action = int(parts[0])
            r, c = int(parts[1]), int(parts[2])
            val = int(parts[3])
            
            if action == 0: # Enemy Attack
                self.handle_enemy_attack(r, c)
            
            elif action == 4: # Feedback Result
                if self.last_action == "ATTACK":
                    self.enemy_view[r][c] = 'X' if val else 'O'
                    self.history.append("HIT!" if val else "Miss.")
                else:
                    self.history.append(f"Radar found {val} targets.")
                self.my_turn = False

            elif action in [1,2,3,5]: # Enemy Radar Request
                found = self.scan_logic(r, c, action)
                self.send_command(f"ACT:4,{r},{c},{found}") # Send Summary
                self.my_turn = True

            elif action == 6: # Radar Reveal Hit (Visual only)
                self.enemy_view[r][c] = 'R'
            
            elif action == 7: # GAME OVER SIGNAL (Enemy Lost)
                self.game_over_screen(winner=True)

    def handle_enemy_attack(self, r, c):
        hit_ship = None
        if self.my_board[r][c] == 1:
            for ship in self.my_ships_list:
                if (r,c) in ship: hit_ship = ship; break
        
        if hit_ship: # ONE HIT SINK ALL
            damage = 0
            for (sr, sc) in hit_ship:
                if self.my_board[sr][sc] != 'H':
                    self.my_board[sr][sc] = 'H'
                    self.send_command(f"ACT:4,{sr},{sc},1")
                    damage += 1
            
            self.total_health -= damage
            self.history.append(f"SHIP AT ({r},{c}) DESTROYED! HP: {self.total_health}")
            self.my_turn = True

            if self.total_health <= 0:
                self.send_command(f"ACT:7,0,0,0")
                self.game_over_screen(winner=False)
        else:
            if self.my_board[r][c] != 'H':
                self.my_board[r][c] = 'M'
                self.send_command(f"ACT:4,{r},{c},0")
                self.history.append(f"Enemy missed at ({r},{c})")
                self.my_turn = True

    def scan_logic(self, r, c, mode):
        count = 0
        detected_coords = []
        for i in range(r-1, r+2):
            for j in range(c-1, c+2):
                if 0<=i<10 and 0<=j<10:
                    match = False
                    if mode==5: match=True
                    elif mode==1 and i==r: match=True
                    elif mode==2 and j==c: match=True
                    elif mode==3 and abs(i-r)==abs(j-c): match=True
                    
                    if match and self.my_board[i][j]==1:
                        self.send_command(f"ACT:6,{i},{j},1") # Reveal to Enemy
                        detected_coords.append(f"({i},{j})")
                        count+=1
        
        # --- THÊM PHẦN NÀY ĐỂ THÔNG BÁO CHO BẢN THÂN BIẾT TÀU NÀO BỊ LỘ ---
        if count > 0:
            coord_str = " ".join(detected_coords)
            self.history.append(f"ALERT! Enemy Radar revealed: {coord_str}")
        else:
            self.history.append("Enemy Radar scanned but found nothing.")
        
        return count

    def place_ships(self):
        self.my_ships_list = []
        self.total_health = 0
        ships = [("Carrier",1,3), ("Battleship",2,2), ("Cruiser",2,3)]
        
        for name, h, w in ships:
            placed = False
            while not placed and self.running:
                self.draw_ui()
                print(f" PLACING {name} ({h}x{w})")
                key = self.get_key()
                if key=='q': self.running=False; return
                
                if key=='\x1b[A': self.cursor[0] = max(0, self.cursor[0]-1)
                elif key=='\x1b[B': self.cursor[0] = min(9, self.cursor[0]+1)
                elif key=='\x1b[D': self.cursor[1] = max(0, self.cursor[1]-1)
                elif key=='\x1b[C': self.cursor[1] = min(9, self.cursor[1]+1)
                elif key=='\r':
                    r,c = self.cursor[0], self.cursor[1]
                    if r+h<=10 and c+w<=10:
                        coords = []
                        collision = False
                        # Kiểm tra va chạm kỹ hơn
                        for i in range(r,r+h):
                            for j in range(c,c+w):
                                if self.my_board[i][j]==1: collision=True
                                coords.append((i,j))
                        
                        if not collision:
                            for (i,j) in coords: self.my_board[i][j]=1
                            self.my_ships_list.append(coords)
                            self.total_health += len(coords)
                            placed=True
                        else:
                            self.history.append(f"ERROR: Overlap at ({r},{c})! Try elsewhere.")
                    else:
                        self.history.append("ERROR: Ship goes out of bounds!")
        
        self.game_state = "PLAYING"
        self.history.append("Ships Ready! Fight!")

    def game_over_screen(self, winner):
        self.game_state = "GAME_OVER"
        self.draw_ui()
        print("\n" + "="*60)
        if winner:
            print("  VICTORY! YOU DESTROYED ALL ENEMY SHIPS!  ".center(60, '*'))
        else:
            print("  DEFEAT! YOUR FLEET HAS BEEN SUNK!  ".center(60, 'X'))
        print("="*60)
        print(" Play Again? Press [Y] to Replay, [Q] to Quit.")
        
        while True:
            key = self.get_key().upper()
            if key == 'Q':
                self.send_command("QUIT")
                self.running = False
                break
            elif key == 'Y':
                self.history.append("Waiting for opponent confirmation...")
                self.draw_ui()
                self.send_command("CMD:REPLAY")
                
                timeout = 0
                while not self.opponent_ready_replay and self.running:
                    time.sleep(0.1)
                    timeout += 1
                    if timeout % 10 == 0: self.draw_ui()
                
                if self.running:
                    pid = self.player_id
                    self.reset_game_state()
                    self.player_id = pid 
                    self.my_turn = True if pid == 1 else False
                    self.game_state = "PLACING"
                    self.history.append("RESTARTING GAME...")
                    break

    def run(self):
        try:
            self.client.connect(('127.0.0.1', 65432))
            threading.Thread(target=self.handle_network, daemon=True).start()
            while self.running:
                if self.game_state == "CONNECTING": self.draw_ui(); time.sleep(0.5)
                elif self.game_state == "PLACING": self.place_ships()
                elif self.game_state == "PLAYING":
                    self.draw_ui()
                    key = self.get_key().upper()
                    if key=='Q': self.send_command("QUIT"); break
                    if not self.my_turn: continue
                    
                    if key=='\x1b[A': self.cursor[0] = max(0, self.cursor[0]-1)
                    elif key=='\x1b[B': self.cursor[0] = min(9, self.cursor[0]+1)
                    elif key=='\x1b[D': self.cursor[1] = max(0, self.cursor[1]-1)
                    elif key=='\x1b[C': self.cursor[1] = min(9, self.cursor[1]+1)
                    
                    cmd = None
                    if key=='\r': 
                        cmd = f"ACT:0,{self.cursor[0]},{self.cursor[1]},0"; self.last_action="ATTACK"
                    elif key=='S' and not self.used_scan_3x3:
                        cmd = f"ACT:5,{self.cursor[0]},{self.cursor[1]},0"; self.used_scan_3x3=True; self.last_action="SKILL"
                    elif key in ['A','D','W'] and not self.used_leak:
                        mode = {'A':2, 'D':1, 'W':3}[key]
                        cmd = f"ACT:{mode},{self.cursor[0]},{self.cursor[1]},0"; self.used_leak=True; self.last_action="SKILL"
                    if cmd:
                        self.send_command(cmd)
                        self.my_turn = False
        except Exception as e: print(e)
        finally: self.client.close()

if __name__ == "__main__":
    BattleshipClient().run()
