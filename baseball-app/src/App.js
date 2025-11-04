import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const [gameStarted, setGameStarted] = useState(false);
  
  // 팀 정보
  const [awayTeamName, setAwayTeamName] = useState('Away Team');
  const [homeTeamName, setHomeTeamName] = useState('Home Team');
  
  // 라인업
  const [awayLineup, setAwayLineup] = useState(['', '', '', '', '', '', '', '', '']);
  const [homeLineup, setHomeLineup] = useState(['', '', '', '', '', '', '', '', '']);
  
  // 현재 타순 (추가!)
  const [currentAwayBatter, setCurrentAwayBatter] = useState(0);
  const [currentHomeBatter, setCurrentHomeBatter] = useState(0);
  
  // 게임 상태
  const [gameState, setGameState] = useState({
    inning: '1회 초',
    outs: 0,
    balls: 0,
    strikes: 0,
    home: 0,
    away: 0,
    runners: [],
    current_batter: null,
    game_over: false
  });
  
  // 이벤트 로그
  const [eventLog, setEventLog] = useState([]);
  const logsEndRef = useRef(null);

  // 로그가 업데이트될 때마다 자동 스크롤 (최신 항목이 위에 오므로 맨 위로)
  useEffect(() => {
    // 로그 컨테이너의 맨 위로 스크롤
    const logContainer = document.querySelector('.event-log');
    if (logContainer) {
      logContainer.scrollTop = 0;
    }
  }, [eventLog]);

  // WebSocket 연결
  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:5000');
    
    websocket.onopen = () => {
      console.log('✅ WebSocket Connected');
      setConnected(true);
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('📥 Received:', data);
      
      if (data.type === 'STATE') {
        setGameState(data);
      } else if (data.type === 'ACK') {
        if (data.msg === 'LINEUP_SET') {
          console.log('✅ 라인업 설정 완료');
        } else if (data.msg === 'RESET') {
          setGameStarted(false);
          setEventLog([]);
          setCurrentAwayBatter(0);
          setCurrentHomeBatter(0);
        } else {
          // 타석 결과 로그 추가 (최신 항목이 위로!)
          const emoji = getResultEmoji(data.result);
          setEventLog(prev => [{
            text: `${emoji} ${data.batter}: ${data.result}`,
            score: `${data.away} - ${data.home}`
          }, ...prev]); // 앞에 추가!
        }
      } else if (data.type === 'END') {
        setEventLog(prev => [{
          text: `🏆 게임 종료! 승자: ${data.winner === 'HOME' ? homeTeamName : awayTeamName}`,
          score: `최종 ${data.away} - ${data.home}`
        }, ...prev]); // 앞에 추가!
      }
    };
    
    websocket.onclose = () => {
      console.log('❌ WebSocket Disconnected');
      setConnected(false);
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, [homeTeamName, awayTeamName]);

  const getResultEmoji = (result) => {
    const emojiMap = {
      'HR': '💥', '3B': '⚡', '2B': '💨', '1B': '✅',
      'OUT': '❌', 'STRIKE': '⚾', 'BALL': '🟢', 'FOUL': '🔶'
    };
    return emojiMap[result] || '📝';
  };

  // 라인업 추가
  const addPlayerToLineup = (team) => {
    if (team === 'away') {
      setAwayLineup([...awayLineup, '']);
    } else {
      setHomeLineup([...homeLineup, '']);
    }
  };

  // 라인업 삭제
  const removePlayerFromLineup = (team, index) => {
    if (team === 'away') {
      setAwayLineup(awayLineup.filter((_, i) => i !== index));
    } else {
      setHomeLineup(homeLineup.filter((_, i) => i !== index));
    }
  };

  // 라인업 수정
  const updatePlayerInLineup = (team, index, value) => {
    if (team === 'away') {
      const newLineup = [...awayLineup];
      newLineup[index] = value;
      setAwayLineup(newLineup);
    } else {
      const newLineup = [...homeLineup];
      newLineup[index] = value;
      setHomeLineup(newLineup);
    }
  };

  // 게임 시작
  const startGame = () => {
    if (!ws || !connected) {
      alert('서버에 연결되지 않았습니다!');
      return;
    }

    // 빈 칸이 아닌 선수만 필터링
    const awayFiltered = awayLineup.filter(p => p.trim() !== '');
    const homeFiltered = homeLineup.filter(p => p.trim() !== '');

    if (awayFiltered.length === 0 || homeFiltered.length === 0) {
      alert('최소 1명 이상의 선수를 입력해주세요!');
      return;
    }

    // 타순 번호 자동 추가
    const awayWithNumbers = awayFiltered.map((name, i) => `${i + 1}. ${name.replace(/^\d+\.\s*/, '')}`);
    const homeWithNumbers = homeFiltered.map((name, i) => `${i + 1}. ${name.replace(/^\d+\.\s*/, '')}`);

    ws.send(JSON.stringify({
      type: 'SET_LINEUP',
      away_lineup: awayWithNumbers,
      home_lineup: homeWithNumbers
    }));

    setGameStarted(true);
    setEventLog([{ text: '⚾ 게임 시작!', score: '0 - 0' }]);
    setCurrentAwayBatter(0);
    setCurrentHomeBatter(0);
  };

  // 게임 리셋
  const resetGame = () => {
    if (ws && connected) {
      ws.send(JSON.stringify({ type: 'RESET' }));
      setGameStarted(false);
      setEventLog([]);
      setCurrentAwayBatter(0);
      setCurrentHomeBatter(0);
    }
  };

  // 타석 결과 입력 (자동으로 타자 이름 추가!)
  const sendResult = (result) => {
    if (ws && connected && gameStarted) {
      // 현재 공격팀 확인
      const isAway = gameState.inning.includes('초');
      const lineup = isAway ? awayLineup : homeLineup;
      const currentIndex = isAway ? currentAwayBatter : currentHomeBatter;
      
      // 빈 칸이 아닌 선수만 필터링
      const validLineup = lineup.filter(p => p.trim() !== '');
      
      if (validLineup.length === 0) {
        alert('라인업이 비어있습니다!');
        return;
      }
      
      // 타순 순환 (1번 → 2번 → ... → 9번 → 1번)
      const batterIndex = currentIndex % validLineup.length;
      const batterName = `${batterIndex + 1}. ${validLineup[batterIndex].replace(/^\d+\.\s*/, '')}`;
      
      // 서버에 전송
      ws.send(JSON.stringify({
        type: 'AB',
        batter: batterName,  // 자동으로 타자 이름 추가!
        result: result
      }));
      
      // 타자가 바뀌는 결과인 경우 다음 타자로
      if (['OUT', '1B', '2B', '3B', 'HR', 'SAC_FLY', 'SAC_BUNT', 'CAUGHT_STEALING'].includes(result)) {
        if (isAway) {
          setCurrentAwayBatter(currentAwayBatter + 1);
        } else {
          setCurrentHomeBatter(currentHomeBatter + 1);
        }
      }
    }
  };

  // 라인업 설정 화면
  if (!gameStarted) {
    return (
      <div className="app">
        <div className="container">
          {/* 헤더 */}
          <div className="header">
            <div className="header-content">
              <div className="header-title">
                <span className="icon">⚾</span>
                <h1>야구 경기 기록 시스템</h1>
              </div>
              <div className={`status ${connected ? 'connected' : 'disconnected'}`}>
                {connected ? '🟢 연결됨' : '🔴 연결 끊김'}
              </div>
            </div>
          </div>

          {/* 라인업 설정 */}
          <div className="lineup-grid">
            {/* Away Team */}
            <div className="team-section">
              <div className="team-name-input">
                <label>Away Team 이름</label>
                <input
                  type="text"
                  value={awayTeamName}
                  onChange={(e) => setAwayTeamName(e.target.value)}
                  placeholder="팀 이름 입력"
                />
              </div>

              <div className="lineup-section">
                <div className="lineup-header">
                  <h3>라인업</h3>
                  <button onClick={() => addPlayerToLineup('away')} className="btn-add">
                    ➕ 추가
                  </button>
                </div>

                <div className="player-list">
                  {awayLineup.map((player, index) => (
                    <div key={index} className="player-item">
                      <span className="player-number">{index + 1}</span>
                      <input
                        type="text"
                        value={player}
                        onChange={(e) => updatePlayerInLineup('away', index, e.target.value)}
                        placeholder="선수 이름"
                      />
                      <button
                        onClick={() => removePlayerFromLineup('away', index)}
                        className="btn-remove"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Home Team */}
            <div className="team-section">
              <div className="team-name-input">
                <label>Home Team 이름</label>
                <input
                  type="text"
                  value={homeTeamName}
                  onChange={(e) => setHomeTeamName(e.target.value)}
                  placeholder="팀 이름 입력"
                />
              </div>

              <div className="lineup-section">
                <div className="lineup-header">
                  <h3>라인업</h3>
                  <button onClick={() => addPlayerToLineup('home')} className="btn-add-home">
                    ➕ 추가
                  </button>
                </div>

                <div className="player-list">
                  {homeLineup.map((player, index) => (
                    <div key={index} className="player-item">
                      <span className="player-number">{index + 1}</span>
                      <input
                        type="text"
                        value={player}
                        onChange={(e) => updatePlayerInLineup('home', index, e.target.value)}
                        placeholder="선수 이름"
                      />
                      <button
                        onClick={() => removePlayerFromLineup('home', index)}
                        className="btn-remove"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 게임 시작 버튼 */}
          <div className="start-button-container">
            <button
              onClick={startGame}
              disabled={!connected}
              className="btn-start"
            >
              ▶️ 게임 시작
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 게임 진행 화면
  return (
    <div className="app">
      <div className="game-container">
        {/* 스코어보드 */}
        <div className="scoreboard">
          <div className="score-grid">
            {/* Away Team */}
            <div className="team-score">
              <div className="team-name">{awayTeamName}</div>
              <div className="score">{gameState.away}</div>
            </div>

            {/* 게임 정보 */}
            <div className="game-info">
              <div className="inning">{gameState.inning}</div>
              <div className="count-info">
                <div className="count-item">
                  <div className="count-label">Out</div>
                  <div className="count-value">{gameState.outs}</div>
                </div>
                <div className="count-item">
                  <div className="count-label">Count</div>
                  <div className="count-value">B{gameState.balls}-S{gameState.strikes}</div>
                </div>
              </div>
            </div>

            {/* Home Team */}
            <div className="team-score">
              <div className="team-name">{homeTeamName}</div>
              <div className="score">{gameState.home}</div>
            </div>
          </div>

          {/* 베이스 상황 */}
          <div className="bases">
            <div className="diamond">
              <div className="base base-2">{gameState.runners.includes('2B') ? '●' : '○'}</div>
              <div className="base base-1">{gameState.runners.includes('1B') ? '●' : '○'}</div>
              <div className="base base-3">{gameState.runners.includes('3B') ? '●' : '○'}</div>
            </div>
          </div>

          {/* 현재 타자 */}
          {gameState.current_batter && (
            <div className="current-batter">
              타자: <strong>{gameState.current_batter}</strong>
            </div>
          )}
        </div>

        <div className="game-grid">
          {/* 타석 결과 입력 */}
          <div className="controls-section">
            <h3>타석 결과 입력</h3>
            
            <div className="control-groups">
              <div className="control-group">
                <div className="group-label">안타</div>
                <div className="button-row">
                  <button onClick={() => sendResult('1B')} className="btn-hit">1루타</button>
                  <button onClick={() => sendResult('2B')} className="btn-hit">2루타</button>
                  <button onClick={() => sendResult('3B')} className="btn-hit">3루타</button>
                  <button onClick={() => sendResult('HR')} className="btn-hr">홈런</button>
                </div>
              </div>

              <div className="control-group">
                <div className="group-label">카운트</div>
                <div className="button-row">
                  <button onClick={() => sendResult('STRIKE')} className="btn-strike">스트라이크</button>
                  <button onClick={() => sendResult('BALL')} className="btn-ball">볼</button>
                  <button onClick={() => sendResult('FOUL')} className="btn-foul">파울</button>
                  <button onClick={() => sendResult('OUT')} className="btn-out">아웃</button>
                </div>
              </div>

              <div className="control-group">
                <div className="group-label">특수</div>
                <div className="button-row">
                  <button onClick={() => sendResult('SAC_FLY')} className="btn-special">희생플라이</button>
                  <button onClick={() => sendResult('SAC_BUNT')} className="btn-special">희생번트</button>
                  <button onClick={() => sendResult('ERROR')} className="btn-special">에러</button>
                  <button onClick={() => sendResult('STEAL')} className="btn-special">도루</button>
                </div>
              </div>

              <div className="control-group">
                <div className="group-label">기타</div>
                <div className="button-row">
                  <button onClick={() => sendResult('CAUGHT_STEALING')} className="btn-other">도루실패</button>
                  <button onClick={() => sendResult('WILD_PITCH')} className="btn-other">폭투</button>
                  <button onClick={() => sendResult('BALK')} className="btn-other">보크</button>
                  <button onClick={resetGame} className="btn-reset">🔄 리셋</button>
                </div>
              </div>
            </div>
          </div>

          {/* 이벤트 로그 */}
          <div className="log-section">
            <h3>경기 기록</h3>
            <div className="event-log">
              {eventLog.map((event, index) => (
                <div key={index} className="log-item">
                  <div className="log-text">{event.text}</div>
                  <div className="log-score">{event.score}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;