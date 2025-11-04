#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
from datetime import datetime

PORT = 5000
LOG_FILE = "game_log_websocket.jsonl"
clients = set()
state = {}

def init_state():
    return {
        "inning": 1,
        "half": "AWAY",
        "outs": 0,
        "balls": 0,
        "strikes": 0,
        "home": 0,
        "away": 0,
        "runners": set(),
        "current_batter": None,
        "game_over": False,
        "away_index": 0,
        "home_index": 0,
    }

state = init_state()

def log_event(data):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        line = json.dumps({"timestamp": datetime.now().isoformat(), "data": data}, ensure_ascii=False)
        f.write(line + "\n")

def runners_list():
    return [b for b in ["1B", "2B", "3B"] if b in state["runners"]]

def reset_count():
    state["balls"] = 0
    state["strikes"] = 0

def advance_half():
    state["outs"] = 0
    reset_count()
    state["runners"].clear()
    state["current_batter"] = None
    if state["half"] == "AWAY":
        state["half"] = "HOME"
    else:
        state["half"] = "AWAY"
        state["inning"] += 1

def score_run(n=1):
    if state["half"] == "AWAY":
        state["away"] += n
    else:
        state["home"] += n

def advance_runners(bases):
    new_runners = set()
    scored = 0
    for r in list(state["runners"]):
        pos = {"1B":1,"2B":2,"3B":3}.get(r,0)
        if not pos: continue
        new_pos = pos + bases
        if new_pos >= 4:
            scored += 1
        elif new_pos == 1: new_runners.add("1B")
        elif new_pos == 2: new_runners.add("2B")
        elif new_pos == 3: new_runners.add("3B")
    state["runners"] = new_runners
    score_run(scored)
    return scored

def check_game_over():
    if state["inning"] >= 9 and state["half"] == "HOME":
        if state["home"] > state["away"]:
            state["game_over"] = True
            return {"type": "END", "winner": "HOME", "home": state["home"], "away": state["away"]}
    if state["inning"] > 9 and state["half"] == "AWAY" and state["outs"] >= 3:
        if state["home"] > state["away"]:
            state["game_over"] = True
            return {"type": "END", "winner": "HOME", "home": state["home"], "away": state["away"]}
        elif state["away"] > state["home"]:
            state["game_over"] = True
            return {"type": "END", "winner": "AWAY", "home": state["home"], "away": state["away"]}
    return None

def next_batter():
    if state["half"] == "AWAY":
        lineup = state.get("away_lineup", [])
        idx = state.get("away_index", 0)
        if lineup:
            batter = lineup[idx % len(lineup)]
            state["away_index"] = (idx + 1) % len(lineup)
            return batter
    else:
        lineup = state.get("home_lineup", [])
        idx = state.get("home_index", 0)
        if lineup:
            batter = lineup[idx % len(lineup)]
            state["home_index"] = (idx + 1) % len(lineup)
            return batter
    return "Unknown"

def apply_ab(batter: str, result: str):
    """타석 결과 처리"""
    if state.get("game_over"):
        return {"type": "ERROR", "msg": "게임이 이미 종료되었습니다"}
    
    result = result.upper()

    # 타자 이름 처리
    if batter:
        state["current_batter"] = batter
    elif not state.get("current_batter"):
        state["current_batter"] = next_batter()

    batter_name = state["current_batter"]

    if result == "OUT":
        state["outs"] += 1
        reset_count()
        state["current_batter"] = None

    elif result == "STRIKE":
        state["strikes"] += 1
        if state["strikes"] >= 3:
            state["outs"] += 1
            reset_count()
            state["current_batter"] = None

    elif result == "BALL":
        state["balls"] += 1
        if state["balls"] >= 4:
            # 4사구 처리
            new_runners = set()
            if "3B" in state["runners"] and "2B" in state["runners"] and "1B" in state["runners"]:
                score_run()
                new_runners.add("3B")
                new_runners.add("2B")
            elif "2B" in state["runners"] and "1B" in state["runners"]:
                new_runners.add("3B")
                new_runners.add("2B")
            elif "1B" in state["runners"]:
                new_runners.add("2B")
            if "3B" in state["runners"] and "1B" not in state["runners"]:
                new_runners.add("3B")
            if "2B" in state["runners"] and "1B" not in state["runners"]:
                new_runners.add("2B")
            
            new_runners.add("1B")
            state["runners"] = new_runners
            reset_count()
            state["current_batter"] = None

    elif result == "FOUL":
        if state["strikes"] < 2:
            state["strikes"] += 1

    elif result == "1B":
        advance_runners(1)
        state["runners"].add("1B")
        reset_count()
        state["current_batter"] = None

    elif result == "2B":
        advance_runners(2)
        state["runners"].add("2B")
        reset_count()
        state["current_batter"] = None

    elif result == "3B":
        advance_runners(3)
        state["runners"].add("3B")
        reset_count()
        state["current_batter"] = None

    elif result == "HR":
        score_run(1 + len(state["runners"]))
        state["runners"].clear()
        reset_count()
        state["current_batter"] = None

    elif result == "SAC_FLY":
        state["outs"] += 1
        if "3B" in state["runners"]:
            score_run()
            state["runners"].discard("3B")
        reset_count()
        state["current_batter"] = None

    elif result == "SAC_BUNT":
        state["outs"] += 1
        advance_runners(1)
        reset_count()
        state["current_batter"] = None

    elif result == "ERROR":
        advance_runners(1)
        state["runners"].add("1B")
        reset_count()
        state["current_batter"] = None

    elif result == "STEAL":
        if "1B" in state["runners"] and "2B" not in state["runners"]:
            state["runners"].discard("1B")
            state["runners"].add("2B")
        elif "2B" in state["runners"] and "3B" not in state["runners"]:
            state["runners"].discard("2B")
            state["runners"].add("3B")

    elif result == "CAUGHT_STEALING":
        state["outs"] += 1
        if "1B" in state["runners"]:
            state["runners"].discard("1B")
        elif "2B" in state["runners"]:
            state["runners"].discard("2B")

    elif result == "WILD_PITCH":
        state["balls"] += 1
        if state["balls"] >= 4:
            # 4볼 처리
            new_runners = set()
            if "3B" in state["runners"] and "2B" in state["runners"] and "1B" in state["runners"]:
                score_run()
                new_runners.add("3B")
                new_runners.add("2B")
            elif "2B" in state["runners"] and "1B" in state["runners"]:
                new_runners.add("3B")
                new_runners.add("2B")
            elif "1B" in state["runners"]:
                new_runners.add("2B")
            if "3B" in state["runners"] and "1B" not in state["runners"]:
                new_runners.add("3B")
            if "2B" in state["runners"] and "1B" not in state["runners"]:
                new_runners.add("2B")
            new_runners.add("1B")
            state["runners"] = new_runners
            reset_count()
            state["current_batter"] = None
        else:
            advance_runners(1)

    elif result == "BALK":
        advance_runners(1)

    # 3아웃 체크
    if state["outs"] >= 3:
        advance_half()
    
    # 게임 종료 체크
    game_end = check_game_over()
    if game_end:
        return game_end

    return {
        "type": "ACK",
        "batter": batter_name,
        "result": result,
        "home": state["home"],
        "away": state["away"],
        "inning": state["inning"],
        "half": state["half"]
    }

def current_state():
    """현재 게임 상태 반환"""
    half_str = "초" if state["half"] == "AWAY" else "말"
    return {
        "type": "STATE",
        "inning": f"{state['inning']}회 {half_str}",
        "outs": state["outs"],
        "balls": state["balls"],
        "strikes": state["strikes"],
        "home": state["home"],
        "away": state["away"],
        "runners": runners_list(),
        "current_batter": state.get("current_batter"),
        "game_over": state.get("game_over", False)
    }

async def broadcast(message):
    """모든 연결된 클라이언트에게 메시지 전송"""
    if clients:
        await asyncio.gather(
            *[client.send(message) for client in clients],
            return_exceptions=True
        )

async def handler(websocket):
    """클라이언트 연결 처리"""
    clients.add(websocket)
    print(f"[JOIN] {websocket.remote_address} (총 {len(clients)}명 접속)")
    
    try:
        # 접속 시 현재 상태 전송
        await websocket.send(json.dumps(current_state(), ensure_ascii=False))
        
        async for message in websocket:
            try:
                evt = json.loads(message)
                t = evt.get("type", "").upper()
                
                if t == "AB":
                    # 타석 결과 처리
                    batter = evt.get("batter", "")
                    result = evt.get("result", "")
                    res = apply_ab(batter, result)
                    
                    # 로그 기록
                    log_event(res)
                    
                    # ACK 전송
                    await websocket.send(json.dumps(res, ensure_ascii=False))
                    
                    # 모든 클라이언트에게 상태 브로드캐스트
                    state_msg = json.dumps(current_state(), ensure_ascii=False)
                    log_event(current_state())
                    await broadcast(state_msg)
                    
                elif t == "SCORE":
                    # 현재 점수판 요청
                    await websocket.send(json.dumps(current_state(), ensure_ascii=False))
                    
                elif t == "RESET":
                    # 게임 리셋
                    global state
                    state = init_state()
                    log_event({"type": "ACK", "msg": "RESET"})
                    
                    # 모든 클라이언트에게 리셋 알림
                    reset_msg = json.dumps({"type": "ACK", "msg": "RESET"}, ensure_ascii=False)
                    await broadcast(reset_msg)
                    
                    # 초기 상태 전송
                    state_msg = json.dumps(current_state(), ensure_ascii=False)
                    await broadcast(state_msg)
                    
                elif t == "SET_RUNNERS":
                    # 주자 수동 조정
                    runners = evt.get("runners", [])
                    state["runners"] = set(runners)
                    
                    # 모든 클라이언트에게 업데이트된 상태 전송
                    state_msg = json.dumps(current_state(), ensure_ascii=False)
                    await broadcast(state_msg)
                    
                elif t == "SET_LINEUP":
                    # 라인업 설정
                    away_lineup = evt.get("away_lineup", [])
                    home_lineup = evt.get("home_lineup", [])
                    
                    # 라인업을 전역 변수로 저장
                    state["away_lineup"] = away_lineup
                    state["home_lineup"] = home_lineup
                    
                    # 확인 메시지 전송
                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "msg": "LINEUP_SET",
                        "away_lineup": away_lineup,
                        "home_lineup": home_lineup
                    }, ensure_ascii=False))
                    
                    print(f"[LINEUP] Away: {away_lineup}")
                    print(f"[LINEUP] Home: {home_lineup}")
                else:
                    await websocket.send(json.dumps({"type": "ERROR", "msg": "Unknown command"}, ensure_ascii=False))
                    
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"type": "ERROR", "msg": "Bad JSON"}, ensure_ascii=False))
                
    except websockets.exceptions.ConnectionClosed:
        print(f"[LEAVE] {websocket.remote_address}")
    finally:
        clients.remove(websocket)
        print(f"[INFO] 남은 접속자: {len(clients)}명")

async def main():
    """서버 시작"""
    print("="*50)
    print("🏟️  야구 경기 기록 시스템 - WebSocket 서버")
    print("="*50)
    print(f"📡 서버 주소: ws://0.0.0.0:{PORT}")
    print(f"📝 로그 파일: {LOG_FILE}")
    print("✅ 서버 준비 완료! 클라이언트 접속 대기 중...")
    print("="*50)
    
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # 무한 대기

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n서버를 종료합니다...")