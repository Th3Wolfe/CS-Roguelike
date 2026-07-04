import { useEffect, useRef, useState } from 'react';
import { get, post } from '../../api/client';
import Button from '../ui/Button';
import '../ui/screenChrome.css';
import './VetoScreen.css';

// Migração da tela de Pick & Ban (ver systems/veto_engine.py pro protocolo
// BO3 completo: ban, ban, pick+lado, pick+lado, ban, ban, decider+coin-flip).
// Ao concluir o veto, essa mesma tela já chama /api/play_series (sem tela de
// táticas ainda — isso fica pra uma próxima migração) e devolve o resultado
// via onComplete, deixando o App decidir o que fazer (voltar pro Hub).
export default function VetoScreen({ team, tactics, onBack, onComplete }) {
  const [mapPool, setMapPool] = useState([]);
  const [veto, setVeto] = useState(null);
  const [opponentName, setOpponentName] = useState('');
  const [opponentProfile, setOpponentProfile] = useState(null);
  const [coinFlipWon, setCoinFlipWon] = useState(null);
  const [log, setLog] = useState([]); // [{actor, action, map}]
  const [error, setError] = useState(null);
  const [playing, setPlaying] = useState(false);
  const logEndRef = useRef(null);

  useEffect(() => {
    Promise.all([get('/api/map_pool'), post('/api/start_veto')]).then(([mp, r]) => {
      setMapPool(mp.maps || []);
      if (!r.ok) { setError(r.error || 'Erro ao iniciar veto'); return; }
      setVeto(r.veto);
      setOpponentName(r.opponent_name);
      setOpponentProfile(r.opp_profile || null);
      setCoinFlipWon(r.coin_flip_won);
      if (r.auto_events?.length) {
        setLog(r.auto_events.map((ev) => ({ actor: ev.actor, action: ev.action, map: ev.map })));
      }
    }).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ block: 'nearest' });
  }, [log]);

  function pushLog(entries) {
    setLog((prev) => [...prev, ...entries]);
  }

  async function handleMapClick(map) {
    if (!veto || veto.needs_side_choice || veto.done) return;
    if (veto.current_actor !== 'player') return;
    const action = veto.current_action;
    const r = await post('/api/veto_action', { action, value: map });
    if (!r.ok) { setError(r.error); return; }
    pushLog([{ actor: 'player', action, map }, ...(r.events || []).map((ev) => ({ actor: ev.actor, action: ev.action, map: ev.map }))]);
    setVeto(r.veto);
  }

  async function handleChooseSide(side) {
    const map = veto.pending_pick_map;
    const r = await post('/api/veto_action', { action: 'side', value: side });
    if (!r.ok) { setError(r.error); return; }
    pushLog([{ actor: 'player', action: 'side', map: `${map} → ${side.toUpperCase()}` }, ...(r.events || []).map((ev) => ({ actor: ev.actor, action: ev.action, map: ev.map }))]);
    setVeto(r.veto);
  }

  async function handlePlaySeries() {
    setPlaying(true);
    setError(null);
    try {
      // /api/tactics_info precisa ser chamado de novo aqui (não só quando a
      // TacticsPanel montou) porque agora o veto já terminou — o backend usa
      // os mapas/lados reais do veto (state["veto_maps"], setado quando o
      // veto termina) para pré-gerar as táticas do time adversário mapa a
      // mapa. Chamar antes disso geraria táticas do adversário desalinhadas
      // com os mapas que de fato vão ser jogados.
      const info = await get('/api/tactics_info');
      const enemyByMap = info.ok ? (info.enemy_tactics || {}) : {};

      // Monta {mapIndex: {team_h1, team_h2, enemy_h1, enemy_h2}} a partir da
      // tática CT/T escolhida na Hub + o lado que o time começa em cada mapa
      // (definido durante o próprio veto).
      const tacticsByMap = {};
      picks.forEach((p, i) => {
        const startsCT = p.team_side === 'ct';
        tacticsByMap[i] = {
          team_h1: startsCT ? tactics?.ct : tactics?.t,
          team_h2: startsCT ? tactics?.t : tactics?.ct,
          enemy_h1: enemyByMap[i]?.h1,
          enemy_h2: enemyByMap[i]?.h2,
        };
      });

      const r = await post('/api/play_series', { tactics: tacticsByMap });
      if (!r.ok) { setError(r.error || 'Erro ao jogar a série'); setPlaying(false); return; }
      onComplete(r);
    } catch (err) {
      setError(err.message);
      setPlaying(false);
    }
  }

  if (error && !veto) {
    return (
      <div className="veto-screen">
        <div className="setup-scroll">
          <div style={{ color: 'var(--color-danger)' }}>Erro: {error}</div>
          <Button variant="ghost" onClick={onBack} style={{ marginTop: 16 }}>Voltar</Button>
        </div>
      </div>
    );
  }

  if (!veto) {
    return (
      <div className="veto-screen">
        <div className="setup-scroll">
          <div style={{ color: 'var(--text2)' }}>Sorteando quem começa o veto…</div>
        </div>
      </div>
    );
  }

  const bans = new Set(veto.bans || []);
  const picks = veto.picks || [];
  const pickedMap = Object.fromEntries(picks.map((p) => [p.map, p]));
  const full = team?.full_maps || [];
  const half = team?.half_maps || [];
  const isPlayerTurn = !veto.needs_side_choice && veto.current_actor === 'player' && !veto.done;

  let instruction;
  if (veto.done) {
    instruction = 'Veto concluído!';
  } else if (veto.needs_side_choice && veto.pending_side_for === 'player') {
    instruction = `Escolha seu lado em ${veto.pending_pick_map}`;
  } else if (veto.current_actor === 'player') {
    instruction = veto.current_action === 'ban'
      ? '🚫 Sua vez — escolha um mapa para BANIR'
      : '✅ Sua vez — escolha um mapa para JOGAR';
  } else if (veto.current_actor === 'opponent') {
    instruction = `⏳ ${opponentName} está escolhendo…`;
  } else {
    instruction = 'Aguardando…';
  }

  const sideLbl = opponentProfile?.side_pref === 'ct' ? 'prefere começar CT'
    : opponentProfile?.side_pref === 't' ? 'prefere começar T'
    : 'não tem preferência de lado';

  return (
    <div className="veto-screen">
      <div className="screen-topbar">
        <div className="screen-topbar-left">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
            Hub
          </Button>
          <span className="screen-topbar-title">Pick &amp; Ban de Mapas</span>
        </div>
        <div className="screen-topbar-spacer" />
        <span className="screen-topbar-meta">Vete mapas ruins · Escolha os seus favoritos</span>
        <span className="screen-topbar-meta" style={{ marginLeft: 16, color: 'var(--text2)' }}>
          {team?.name || 'Você'} vs {opponentName}
        </span>
      </div>

      <div className="setup-scroll">
        <div className="veto-coin">
          <div style={{ marginBottom: 8 }}>
            {coinFlipWon
              ? <>🪙 <b>Você ganhou o cara-ou-coroa</b> — você vai primeiro no veto.</>
              : <>🪙 <b>{opponentName} ganhou o cara-ou-coroa</b> — eles vão primeiro.</>}
          </div>
          {opponentProfile && (
            <div style={{ fontSize: '.8rem', color: 'var(--text3)', borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 4 }}>
              <b style={{ color: 'var(--text2)' }}>🔍 Scout de {opponentName}:</b>{' '}
              mapas favoritos <span style={{ color: 'var(--green)' }}>{(opponentProfile.preferred || []).join(', ') || '?'}</span> ·{' '}
              evita <span style={{ color: 'var(--red)' }}>{(opponentProfile.disliked || []).join(', ') || '?'}</span> · {sideLbl}
            </div>
          )}
        </div>

        <div className="veto-log">
          {log.map((entry, i) => (
            <div className="veto-log-item" key={i}>
              <span className="vli-actor">{entry.actor === 'player' ? (team?.name || 'Você') : opponentName}</span>
              <span className={`vli-action ${entry.action === 'ban' ? 'vla-ban' : entry.action === 'pick' ? 'vla-pick' : 'vla-side'}`}>
                {entry.action === 'ban' ? 'BANIU' : entry.action === 'pick' ? 'ESCOLHEU' : 'LADO'}
              </span>
              <span className="vli-map">{entry.map}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>

        <div className="veto-instruction">{instruction}</div>

        <div className="veto-map-grid">
          {mapPool.map((m) => {
            const isBanned = bans.has(m);
            const pick = pickedMap[m];
            const isPPlayer = pick?.picker === 'player';
            const isPOpp = pick?.picker === 'opponent';
            const isDecider = pick?.picker === 'decider';
            const profCls = full.includes(m) ? 'vmc-prof-full' : half.includes(m) ? 'vmc-prof-half' : 'vmc-prof-none';
            const profLbl = full.includes(m) ? 'Full' : half.includes(m) ? 'Half' : 'Nula';

            let cardCls = 'veto-map-card';
            let statusTxt = '';
            if (isBanned) { cardCls += ' vmc-banned'; statusTxt = 'BANIDO'; }
            else if (isPPlayer) { cardCls += ' vmc-picked-player'; statusTxt = 'SEU PICK'; }
            else if (isPOpp) { cardCls += ' vmc-picked-opp'; statusTxt = 'PICK DELE'; }
            else if (isDecider) { cardCls += ' vmc-decider'; statusTxt = 'DECIDER'; }
            else if (!isPlayerTurn) { cardCls += ' vmc-disabled'; }

            return (
              <div key={m} className={cardCls} onClick={() => handleMapClick(m)}>
                {statusTxt && <span className="vmc-status">{statusTxt}</span>}
                <div className="vmc-name">{m}</div>
                <span className={`vmc-prof ${profCls}`}>{profLbl}</span>
                {pick && <div style={{ fontSize: '.68rem', color: 'var(--text3)', marginTop: 3 }}>Time: {pick.team_side?.toUpperCase() || '?'}</div>}
              </div>
            );
          })}
        </div>
      </div>

      <div className="setup-action-bar">
        {veto.needs_side_choice && veto.pending_side_for === 'player' && (
          <div className="veto-side-panel">
            <div className="veto-side-title">Escolha seu lado em <span style={{ color: 'var(--text)' }}>{veto.pending_pick_map}</span></div>
            <div style={{ display: 'flex', gap: 12 }}>
              <Button variant="orange" onClick={() => handleChooseSide('ct')}>🛡️ CT</Button>
              <Button variant="ghost" onClick={() => handleChooseSide('t')}>💣 T</Button>
            </div>
          </div>
        )}

        {error && <div style={{ color: 'var(--color-danger)', marginBottom: 10, fontSize: '.85rem' }}>{error}</div>}

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {picks.map((p, i) => (
            <div className="veto-pick-summary" key={i}>
              <div className="vps-map">{p.map}</div>
              <div className="vps-meta">
                {p.picker === 'player' ? 'Seu pick' : p.picker === 'opponent' ? `Pick de ${opponentName}` : 'Decider'}
                {' · Time: '}{p.team_side?.toUpperCase() || '?'}
              </div>
            </div>
          ))}
        </div>

        {veto.done && (
          <Button variant="orange" size="lg" style={{ marginTop: 16 }} disabled={playing} onClick={handlePlaySeries}>
            {playing ? 'Jogando série…' : '▶ Jogar Série'}
          </Button>
        )}
      </div>
    </div>
  );
}
