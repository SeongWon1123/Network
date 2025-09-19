# server_threaded.py
import socket, threading

HOST, PORT = "0.0.0.0", 5000

def handle(conn, addr):
    with conn:
        print(f"[JOIN] {addr}")
        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = data.decode(errors="ignore").strip()
            print(f"[{addr}] {msg}")
            conn.sendall((f"OK {msg}\n").encode())
    print(f"[LEAVE] {addr}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[LISTEN] {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()
