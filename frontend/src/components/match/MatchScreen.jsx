import { useEffect, useRef, useState } from 'react';
import { get, post } from '../../api/client';
import { useMusic } from '../../music/MusicContext';
import Button from '../ui/Button';
import PauseModal from './PauseModal';
import './MatchScreen.css';

// Reescrita pra suportar o Pause Técnico de verdade: em vez de resolver a
// série inteira numa tacada só (como antes), agora cada mapa é resolvido
// individualmente via /api/play_map, e só no fim /api/finish_series grava
// tudo na campanha. Isso permite pausar ENTRE mapas — não no meio de um
// mapa, já que cada /api/play_map já devolve o mapa inteiro (dois halves +
// OT) resolvido de uma vez; mudar tática no meio disso não teria efeito
// real no resultado já calculado, então o pause só é oferecido nos
// intervalos entre mapas (inclusive antes do primeiro).
const SPEED_LEVELS = [
  { label: '🐢 Muito Lento', delay: 1800 },
  { label: '🚶 Lento', delay: 800 },
  { label: '▶ Normal', delay: 300 },
  { label: '⚡ Rápido', delay: 80 },
  { label: '🚀 Turbo', delay: 12 },
];

function sleep(ms) { return new Promise((res) => setTimeout(res, ms)); }

function buildShuffledSeq(wins, losses) {
  const seq = [...Array(wins).fill('win'), ...Array(losses).fill('loss')];
  for (let i = seq.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [seq[i], seq[j]] = [seq[j], seq[i]];
  }
  return seq;
}

export default function MatchScreen({ team, opponentName, initialTactics, onDone }) {
  const { setContext, playOnce } = useMusic();
  useEffect(() => { setContext('match'); }, [setContext]);

  const [info, setInfo] = useState(null);       // {veto_maps, enemy_tactics, ...} de /api/tactics_info
  const [error, setError] = useState(null);
  const [tactics, setTactics] = useState({ ct: initialTactics?.ct, t: initialTactics?.t });
  const [pauseUsed, setPauseUsed] = useState(false);
  const [showPause, setShowPause] = useState(false);

  const [mapIndex, setMapIndex] = useState(0);
  const [phase, setPhase] = useState('loading'); // loading | between | animating | finishing | summary
  const [mapCards, setMapCards] = useState([]);
  const [seriesDots, setSeriesDots] = useState(['pending', 'pending', 'pending']);
  const [banner, setBanner] = useState({ visible: false, text: '' });
  const [finishResult, setFinishResult] = useState(null);
  const [playerStats, setPlayerStats] = useState(null);

  const [speedIdx, setSpeedIdx] = useState(0);
  const speedRef = useRef(0);
  useEffect(() => { speedRef.current = speedIdx; }, [speedIdx]);

  useEffect(() => {
    get('/api/tactics_info').then((r) => {
      if (!r.ok) { setError(r.error || 'Erro ao preparar a partida'); return; }
      setInfo(r);
      setPhase('between');
    }).catch((err) => setError(err.message));
  }, []);

  const displayOpponentName = opponentName || finishResult?.result?.opponent_name || '...';
  const teamName = team?.name || 'Seu Time';
  const totalMaps = info?.veto_maps?.length || 3;

  function updateCard(idx, updater) {
    setMapCards((prev) => prev.map((c, i) => (i === idx ? updater(c) : c)));
  }

  function tacticsForMap(mi) {
    const entry = info.veto_maps[mi];
    const startsCT = entry.team_side === 'ct';
    const e = info.enemy_tactics?.[mi] || info.enemy_tactics?.[String(mi)] || {};
    return {
      team_h1: startsCT ? tactics.ct : tactics.t,
      team_h2: startsCT ? tactics.t : tactics.ct,
      enemy_h1: e.h1,
      enemy_h2: e.h2,
    };
  }

  async function animateHalf(idx, halfKey, teamRounds, oppRounds, side, startT, startO) {
    const total = teamRounds + oppRounds;
    if (total === 0) return;
    const seq = buildShuffledSeq(teamRounds, oppRounds);
    let t = startT, o = startO;
    updateCard(idx, (c) => ({ ...c, scoreT: t, scoreO: o }));
    for (let i = 0; i < seq.length; i++) {
      const won = seq[i] === 'win';
      if (won) t++; else o++;
      const dotSide = won ? side : (side === 'ct' ? 't' : 'ct');
      const tt = t, oo = o;
      updateCard(idx, (c) => ({ ...c, scoreT: tt, scoreO: oo, [halfKey]: [...c[halfKey], dotSide] }));
      await sleep(SPEED_LEVELS[speedRef.current].delay);
    }
  }

  async function playMap() {
    setPhase('animating');
    setError(null);
    const mi = mapIndex;
    const entry = info.veto_maps[mi];

    let r;
    try {
      r = await post('/api/play_map', { map_index: mi, tactics: tacticsForMap(mi) });
    } catch (err) {
      setError(err.message); setPhase('between'); return;
    }
    if (!r.ok) { setError(r.error || 'Erro ao jogar o mapa'); setPhase('between'); return; }

    const map = r.map_result;
    const teamSide = entry.team_side || 'ct';
    const oppSide = teamSide === 'ct' ? 't' : 'ct';

    setMapCards((prev) => [...prev, {
      mapName: map.map_name, wentOT: map.went_ot, teamSide, oppSide,
      scoreT: 0, scoreO: 0, h1Dots: [], h2Dots: [], resultBadge: null, visible: false,
    }]);
    await sleep(150);
    updateCard(mi, (c) => ({ ...c, visible: true }));
    await sleep(250);

    setBanner({ visible: true, text: `${map.map_name} — 1º Half (${teamSide.toUpperCase()})` });
    await animateHalf(mi, 'h1Dots', map.team_half1, map.opp_half1, teamSide, 0, 0);

    setBanner({ visible: true, text: `↔ Troca de lado — ${map.map_name} 2º Half (${oppSide.toUpperCase()})` });
    await sleep(800);

    setBanner({ visible: true, text: `${map.map_name} — 2º Half (${oppSide.toUpperCase()})` });
    await animateHalf(mi, 'h2Dots', map.team_half2, map.opp_half2, oppSide, map.team_half1, map.opp_half1);

    if (map.went_ot && (map.team_ot + map.opp_ot) > 0) {
      setBanner({ visible: true, text: `${map.map_name} — ⚡ OVERTIME` });
      await animateHalf(mi, 'h2Dots', map.team_ot, map.opp_ot, teamSide,
        map.team_half1 + map.team_half2, map.opp_half1 + map.opp_half2);
    }
    setBanner({ visible: false, text: '' });

    const won = map.winner === 'team';
    updateCard(mi, (c) => ({ ...c, resultBadge: won ? 'w' : 'l' }));
    setSeriesDots((prev) => prev.map((d, i) => (i === mi ? (won ? 'w' : 'l') : d)));
    await sleep(400);

    if (r.series_done) {
      await finishSeries();
    } else {
      setMapIndex(mi + 1);
      setPhase('between');
    }
  }

  async function finishSeries() {
    setPhase('finishing');
    try {
      const r = await post('/api/finish_series', {});
      if (!r.ok) { setError(r.error || 'Erro ao fechar a série'); setPhase('between'); return; }
      setFinishResult(r);
      if (r.result.series_detail?.player_stats?.length) {
        setPlayerStats([...r.result.series_detail.player_stats].sort((a, b) => b.kd - a.kd));
      }
      playOnce(r.result.won ? 'victory' : 'defeat');
      setPhase('summary');
    } catch (err) {
      setError(err.message);
      setPhase('between');
    }
  }

  function handlePauseConfirm() {
    setPauseUsed(true);
    setShowPause(false);
  }

  if (error && phase !== 'between') {
    return (
      <div className="match-screen">
        <div className="match-modal"><div className="match-modal-scroll">
          <div style={{ color: 'var(--color-danger)', textAlign: 'center', padding: 24 }}>Erro: {error}</div>
        </div></div>
      </div>
    );
  }

  if (phase === 'loading' || !info) {
    return (
      <div className="match-screen">
        <div className="match-modal"><div className="match-modal-scroll">
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text2)' }}>Preparando a partida…</div>
        </div></div>
      </div>
    );
  }

  return (
    <div className="match-screen">
      <div className="match-modal">
        <div className="match-modal-scroll">
          <div className="mm-header">
            <div className="mm-live">● LIVE</div>
            <div className="mm-matchup">
              <div className="mm-team-name left">{teamName}</div>
              <div className="mm-vs">VS</div>
              <div className="mm-team-name right">{displayOpponentName}</div>
            </div>
            <div className="mm-controls">
              <div className="speed-ctrl" title="Velocidade da simulação">
                <button className="spd-btn" onClick={() => setSpeedIdx((i) => Math.max(0, i - 1))} disabled={speedIdx === 0}>–</button>
                <span>{SPEED_LEVELS[speedIdx].label}</span>
                <button className="spd-btn" onClick={() => setSpeedIdx((i) => Math.min(SPEED_LEVELS.length - 1, i + 1))} disabled={speedIdx === SPEED_LEVELS.length - 1}>+</button>
              </div>
              {phase === 'between' && (
                <button className="pause-btn" disabled={pauseUsed} onClick={() => setShowPause(true)} title={pauseUsed ? 'Pause já usado nesta partida' : 'Rever/trocar tática (uso único)'}>
                  ⏸ Pause {pauseUsed ? '(usado)' : ''}
                </button>
              )}
            </div>
          </div>

          {error && <div style={{ color: 'var(--color-danger)', textAlign: 'center', fontSize: '.8rem', marginBottom: 8 }}>{error}</div>}
          {banner.visible && <div className="mm-half-banner">{banner.text}</div>}

          <div className="series-maps">
            {seriesDots.map((d, i) => (
              <div key={i} className={`sm-dot ${d === 'w' ? 'tw' : d === 'l' ? 'ow' : ''}`}>
                {d === 'w' ? '✓' : d === 'l' ? '✗' : i + 1}
              </div>
            ))}
          </div>

          <div>
            {mapCards.map((c, i) => <MapCard key={i} card={c} teamName={teamName} oppName={displayOpponentName} />)}
          </div>

          {phase === 'between' && (
            <div style={{ textAlign: 'center', margin: '18px 0' }}>
              <Button variant="orange" size="lg" onClick={playMap}>
                ▶ {mapIndex === 0 ? 'Iniciar 1º Mapa' : `Jogar Mapa ${mapIndex + 1}`}
              </Button>
            </div>
          )}
          {phase === 'finishing' && (
            <div style={{ textAlign: 'center', margin: '18px 0', color: 'var(--text2)' }}>Fechando a série…</div>
          )}

          {playerStats && (
            <div className="pst-section">
              <div className="pst-label">Desempenho do Time</div>
              <table className="pst-table">
                <thead><tr><th>Jogador</th><th>K</th><th>D</th><th>K/D</th><th>ADR</th></tr></thead>
                <tbody>
                  {playerStats.map((p, i) => (
                    <tr key={i}>
                      <td><div className="pst-nick">{p.nickname}</div><div className="pst-role">{p.role}</div></td>
                      <td>{p.kills}</td><td>{p.deaths}</td>
                      <td className={p.kd >= 1 ? 'pst-kd-pos' : 'pst-kd-neg'}>{p.kd.toFixed(2)}</td>
                      <td>{p.adr.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {phase === 'summary' && finishResult && (
          <div className="match-summary">
            <div className={`ms-result ${finishResult.result.won ? 'w' : 'l'}`}>
              {finishResult.result.won ? '🏆 VITÓRIA' : '💀 DERROTA'}
            </div>
            <div className="ms-desc">{finishResult.result.description}</div>
            <div className="ms-meta">
              Chance: <b>{Math.round(finishResult.result.win_probability * 100)}%</b> &nbsp;·&nbsp;
              Score: <b>{finishResult.result.team_score.toFixed(1)}</b> vs <b>{finishResult.result.opp_score.toFixed(1)}</b>
            </div>
            <Button variant="orange" onClick={() => onDone(finishResult)}>Continuar →</Button>
          </div>
        )}
      </div>

      {showPause && (
        <PauseModal
          selectedCT={tactics.ct}
          selectedT={tactics.t}
          onSelectCT={(ct) => setTactics((t) => ({ ...t, ct }))}
          onSelectT={(t2) => setTactics((t) => ({ ...t, t: t2 }))}
          onConfirm={handlePauseConfirm}
          mapsRemaining={totalMaps - mapIndex}
        />
      )}
    </div>
  );
}

function MapCard({ card, teamName, oppName }) {
  return (
    <div className={`map-score-card ${card.visible ? 'vis' : ''}`}>
      <div className="msc-head">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="msc-map">{card.mapName}</span>
          {card.wentOT && <span className="msc-ot">OT</span>}
        </div>
        {card.resultBadge && (
          <span className={`msc-result-badge ${card.resultBadge}`}>{card.resultBadge === 'w' ? 'VITÓRIA' : 'DERROTA'}</span>
        )}
      </div>
      <div className="msc-scores">
        <div className="msc-team-lbl">{teamName}</div>
        <div className="score-pair">
          <div className="score-dig t">{card.scoreT}</div>
          <div className="score-colon">:</div>
          <div className="score-dig o">{card.scoreO}</div>
        </div>
        <div className="msc-team-lbl">{oppName}</div>
      </div>
      <div className="round-vis-wrap">
        <div className="round-vis-half">
          <div className="rv-half-label">{card.teamSide.toUpperCase()}</div>
          <div className="round-vis">
            {card.h1Dots.map((s, i) => <div key={i} className={`rv-dot ${s}`} />)}
          </div>
        </div>
        <div className="rv-half-sep" />
        <div className="round-vis-half">
          <div className="rv-half-label">{card.oppSide.toUpperCase()}</div>
          <div className="round-vis">
            {card.h2Dots.map((s, i) => <div key={i} className={`rv-dot ${s}`} />)}
          </div>
        </div>
      </div>
    </div>
  );
}
