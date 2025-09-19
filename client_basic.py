import socket, sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 5000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print(f"[CONNECTED] {HOST}:{PORT} (type and Enter, Ctrl+C to quit)")
    while True:
        line = input("> ")
        s.sendall((line + "\n").encode())
        resp = s.recv(4096).decode(errors="ignore").strip()
        print(f"< {resp}")

