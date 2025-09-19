import socket

HOST = "0.0.0.0"
PORT = 5000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"[LISTEN] {HOST}:{PORT}")
    conn, addr = s.accept()
    with conn:
        print(f"[CONNECT] {addr}")
        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = data.decode(errors="ignore").strip()
            print(f"[RECV] {msg}")
            conn.sendall((msg + "\n").encode())
    print("[CLOSE] client")
