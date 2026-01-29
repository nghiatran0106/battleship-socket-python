# Terminal Battleship Online (TCP Socket) 🚢

A real-time, multiplayer Battleship game played directly in the Linux Terminal. Built with Python using raw TCP Sockets.

**Author:** Tran Phu Nghia
**Student ID:** 20233871

---

## 🔥 Features
* **Real-time Multiplayer:** Uses a Client-Server architecture (TCP/IP).
* **Terminal GUI:** Custom interface using `termios` and ANSI escape codes (no external libraries required).
* **One-Hit Sink Mechanics:** Hitting any part of a ship destroys the **entire ship** instantly.
* **Tactical Radar System:**
    * **Scan (S):** Scans a 3x3 area.
    * **Line Scan (A/D/W):** Scans a specific row, column, or diagonal line.
    * **Visual Feedback:** If a Radar detects a ship, it reveals the specific location with an `[R]` marker.
* **Replay System:** Allows players to restart the match without restarting the server.

## 🛠 Prerequisites
* **OS:** Linux (Ubuntu/Debian) or macOS. (Windows is not supported due to `termios` dependency).
* **Python:** Version 3.6 or higher.

## 🚀 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/battleship-socket.git](https://github.com/YOUR_USERNAME/battleship-socket.git)
    cd battleship-socket
    ```

2.  **Run the Server (Terminal 1):**
    The server handles the connection between two players.
    ```bash
    python3 server.py
    ```

3.  **Start Player 1 (Terminal 2):**
    ```bash
    python3 client.py
    ```
    *Enter Server IP (default `127.0.0.1` for local play).*

4.  **Start Player 2 (Terminal 3):**
    ```bash
    python3 client.py
    ```

## 🎮 How to Play

### Phase 1: Setup
* Use **Arrow Keys** to move the ship.
* Press **Enter** to place the ship.
* You cannot overlap ships.

### Phase 2: Battle
* **Turn-Based:** Player 1 goes first.
* **Winning:** Reduce opponent's HP to 0 (Destroy 3 ships).

### Controls
| Key | Action | Note |
| :--- | :--- | :--- |
| **Arrow Keys** | Move Cursor | Navigate the grid |
| **Enter** | Fire / Select | Attack the selected coordinate |
| **S** | 3x3 Scan | Reveals count of ship cells in 3x3 area |
| **A** | Vertical Scan | Scans vertical line in 3x3 area |
| **D** | Horizontal Scan | Scans horizontal line in 3x3 area |
| **W** | Diagonal Scan | Scans diagonal line in 3x3 area |
| **Q** | Quit | Exit the game safely |

## 📸 Screenshots
*(You can upload screenshots to your repo later and link them here)*

---
*Built for the Computer Architecture / Systems Programming course.*
