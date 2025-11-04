#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 네트워크 기반 야구 경기 기록 시스템 - WebSocket 클라이언트
작성자: 최성원
날짜: 2025-10-12
설명: WebSocket 서버와 통신하는 터미널 클라이언트
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 5000
LOG_FILE = "game_log_client.jsonl"

def result_shortcut(x: str) -> str:
    """입력 단축키를 표준 형식으로 변환"""
    x = x.strip().upper()
    table = {
        # 숫자
        "1": "1B",
        "2": "2B",
        "3": "3B",
        
        # 영문
        "HR": "HR",
        "S": "STRIKE",
        "B": "BALL",
        "F": "FOUL",
        "O": "OUT",
        "SF": "SAC_FLY",
        "SH": "SAC_BUNT",
        "E": "ERROR",
        "SB": "STEAL",
        "CS": "CAUGHT_STEALING",
        "WP": "WILD_PITCH",
        "BK": "BALK",
        
        # 한글 추가
        "홈런": "HR",
        "스트라이크": "STRIKE",
        "스": "STRIKE",
        "볼": "BALL",
        "ㅂ": "BALL",
        "파울": "FOUL",
        "ㅍ": "FOUL",
        "아웃": "OUT",
        "희비": "SAC_FLY",
        "희번": "SAC_BUNT",
        "에러": "ERROR",
        "도루": "STEAL",
        "도루성공": "STEAL",
        "도루실패": "CAUGHT_STEALING",
        "도루아웃": "CAUGHT_STEALING",
        "폭투": "WILD_PITCH",
        "보크": "BALK"
    }
    return table.get(x, x)

def log_event(data: dict):
    """이벤트를 파일에 기록"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        line = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "data": data
        }, ensure_ascii=False)
        f.write(line + "\n")

def render_state(obj: dict):
    """게임 상태를 터미널에 출력"""
    print("="*40)
    print(f"이닝: {obj['inning']}   Outs: {obj['outs']}   Count: B{obj['balls']}-S{obj['strikes']}")
    print(f"점수: Away {obj['away']} - Home {obj['home']}")
    one = "●" if "1B" in obj.get("runners", []) else "○"
    two = "●" if "2B" in obj.get("runners", []) else "○"
    three = "●" if "3B" in obj.get("runners", []) else "○"
    print(f"루 상황: 1루 {one}   2루 {two}   3루 {three}")
    if obj.get("current_batter"):
        print(f"타자: {obj['current_batter']}")
    if obj.get("game_over"):
        print("🏆 게임 종료!")
    print("="*40)

async def receive_messages(websocket, need_batter_input):
    """서버로부터 메시지를 받는 비동기 함수"""
    try:
        async for message in websocket:
            try:
                obj = json.loads(message)
                log_event(obj)
                
                if obj.get("type") == "STATE":
                    render_state(obj)
                    
                elif obj.get("type") == "ACK":
                    if obj.get("msg") == "RESET":
                        print("\n✅ 게임이 리셋되었습니다!")
                        need_batter_input[0] = True
                    else:
                        batter_name = obj.get('batter', '타자')
                        result_type = obj.get('result', '').upper()
                        
                        print(f"\n✅ {batter_name}: {result_type}")
                        print(f"   점수: Away {obj['away']} - Home {obj['home']}")
                        
                        # 타석 결과로 타자가 바뀐 경우
                        if result_type in ['OUT', '1B', '2B', '3B', 'HR', 'SAC_FLY', 'SAC_BUNT', 'CAUGHT_STEALING']:
                            need_batter_input[0] = True
                        # Unknown이 나온 경우 무조건 다음에 타자 입력 받기
                        if batter_name == "Unknown":
                            need_batter_input[0] = True
                            print("⚠️ 다음 타석에서 타자 이름을 입력하세요!")
                        
                elif obj.get("type") == "END":
                    print("\n" + "="*40)
                    print(f"🏆 게임 종료! 승자: {obj['winner']}")
                    print(f"최종 점수: Away {obj['away']} - Home {obj['home']}")
                    print("="*40)
                    need_batter_input[0] = True
                    
                elif obj.get("type") == "ERROR":
                    print(f"\n❌ 오류: {obj.get('msg', '알 수 없는 오류')}")
                    
            except json.JSONDecodeError:
                print(f"⚠️ JSON 파싱 오류: {message}")
                
    except websockets.exceptions.ConnectionClosed:
        print("\n❌ 서버와의 연결이 끊어졌습니다.")

async def send_messages(websocket, need_batter_input):
    """사용자 입력을 받아 서버로 전송하는 비동기 함수"""
    while True:
        try:
            # asyncio에서 input을 사용하기 위해 run_in_executor 사용
            loop = asyncio.get_event_loop()
            cmd = await loop.run_in_executor(None, input, "\n입력 (AB/SCORE/R/Q): ")
            cmd = cmd.strip().upper()
            
            if cmd == "Q":
                print("👋 프로그램을 종료합니다...")
                break
                
            elif cmd == "R":
                await websocket.send(json.dumps({"type": "RESET"}, ensure_ascii=False))
                need_batter_input[0] = True
                
            elif cmd == "SCORE":
                await websocket.send(json.dumps({"type": "SCORE"}, ensure_ascii=False))
                
            elif cmd == "AB":
                batter = ""
                
                # 타자 입력이 필요한 경우에만 물어봄
                if need_batter_input[0]:
                    while not batter:
                        batter = await loop.run_in_executor(None, input, "타자 이름/번호: ")
                        batter = batter.strip()
                        if not batter:
                            print("❌ 타자 이름/번호를 입력해주세요!")
                    need_batter_input[0] = False
                
                print("\n⚾ 결과 입력:")
                print()
                print("  안타: 1=1루타, 2=2루타, 3=3루타, HR=홈런")
                print()
                print("  카운트: S/스=스트라이크, B/볼=볼, F/파=파울, O/아웃=아웃")
                print()
                print("  특수: 희비=희생플라이, 희번=희생번트, 에러=에러")
                print()
                print("  주자: 도루=도루성공, 도루실패=도루실패, 폭투=폭투, 보크=보크")
                print()
                
                res = await loop.run_in_executor(None, input, "결과: ")
                
                obj = {"type": "AB", "result": result_shortcut(res)}
                if batter:
                    obj["batter"] = batter
                    
                await websocket.send(json.dumps(obj, ensure_ascii=False))
                
            else:
                print("❌ 잘못된 명령 (AB/SCORE/R/Q 중 하나를 입력하세요)")
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            break

async def main():
    """메인 함수"""
    uri = f"ws://{HOST}:{PORT}"
    
    print("="*50)
    print("🏟️  야구 경기 기록 시스템 - WebSocket 클라이언트")
    print("="*50)
    print(f"📡 서버 주소: {uri}")
    print(f"📝 로그 파일: {LOG_FILE}")
    print("🔄 서버에 연결 중...")
    print("="*50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ [CONNECTED]")
            print("\n📋 명령어 도움말:")
            print("  AB = 타석 결과 입력")
            print("  SCORE = 현재 점수판 보기")
            print("  R = 게임 리셋")
            print("  Q = 종료\n")
            
            # 타자 입력 필요 여부를 리스트로 감싸서 참조 전달
            need_batter_input = [True]
            
            # 송신과 수신을 동시에 처리
            await asyncio.gather(
                receive_messages(websocket, need_batter_input),
                send_messages(websocket, need_batter_input)
            )
            
    except ConnectionRefusedError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("💡 server_websocket.py가 실행 중인지 확인하세요!")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다...")