# server_json.py
import socket, threading, json

HOST, PORT = "0.0.0.0", 5000

# 간단한 경기 점수 상태
score = {"home": 0, "away": 0}

def apply_event(evt):
    # 타석 결과가 홈런일 때 점수 추가
    if evt.get("type") == "AB" and evt.get("result") == "HR":
        team = evt.get("team")
        if team == "HOME":
            score["home"] += 1
        elif team == "AWAY":
            score["away"] += 1

def handle(conn, addr):
    with conn:
        print(f"[JOIN] {addr}")
        buf = b""
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    evt = json.loads(line.decode())
                except json.JSONDecodeError:
                    conn.sendall(b'{"type":"ERROR","msg":"Bad JSON"}\n')
                    continue

                if evt.get("type") == "AB":
                    apply_event(evt)
                    conn.sendall(b'{"type":"ACK"}\n')
                elif evt.get("type") == "SCORE":
                    resp = json.dumps({"type":"SCORE", **score})
                    conn.sendall((resp + "\n").encode())
                else:
                    conn.sendall(b'{"type":"ERROR","msg":"Unknown type"}\n')

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[LISTEN] {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()
