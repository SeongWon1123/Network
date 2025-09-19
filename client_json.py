# client_json.py
import socket, json, sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 5000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("[CONNECTED]")
    while True:
        cmd = input("입력 (AB=타석, SCORE=점수보기, Q=종료): ").strip().upper()
        if cmd == "Q":
            break
        if cmd == "AB":
            team = input("팀 (HOME/AWAY): ").strip().upper()
            result = input("결과 (1B/2B/HR/OUT): ").strip().upper()
            obj = {"type":"AB","team":team,"result":result}
        elif cmd == "SCORE":
            obj = {"type":"SCORE"}
        else:
            print("잘못된 명령")
            continue
        s.sendall((json.dumps(obj) + "\n").encode())
        resp = s.recv(4096).decode().strip()
        print(f"< {resp}")
