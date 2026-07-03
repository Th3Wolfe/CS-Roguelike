import { useEffect, useRef, useState } from 'react';
import { post } from '../../api/client';
import Button from '../ui/Button';
import {
  ROLE_ORDER, ROLE_EMOJI, ROLE_COLOR, KEY_STATS, STAT_KEYS, flag, SPIN_TEAM_NAMES,
} from '../../constants/roles';
import './DraftScreen.css';

const SPIN_INTERVALS = [50, 55, 60, 70, 80, 100, 120, 150, 180, 220, 270, 320];
const ROLE_TO_SLOT = Object.fromEntries(ROLE_ORDER.map((r, i) => [r, i]));

function shuffledSpinPool() {
  return [...SPIN_TEAM_NAMES].sort(() => Math.random() - 0.5);
}

export default function DraftScreen({ eraId, onBack, onConfirm }) {
  const [picks, setPicks] = useState([]);           // [{slotIdx, player}]
  const [teamPool, setTeamPool] = useState([]);      // 5 jogadores do time sorteado atual
  const [drawnTeamName, setDrawnTeamName] = useState('');
  const [usedTeams, setUsedTeams] = useState([]);
  const [reshuffles, setReshuffles] = useState(3);
  const [teamNameInput, setTeamNameInput] = useState('');
  const [spinning, setSpinning] = useState(true);
  const [spinDisplay, setSpinDisplay] = useState('–');
  const [poolError, setPoolError] = useState(null);
  const spinRunId = useRef(0);

  async function drawNewTeam(exclude) {
    const runId = ++spinRunId.current;
    setSpinning(true);
    setPoolError(null);

    const fetchPromise = post('/api/draft_team', { era_id: eraId, exclude_teams: exclude });
    const spinPool = shuffledSpinPool();
    for (let i = 0; i < SPIN_INTERVALS.length; i++) {
      if (spinRunId.current !== runId) return; // uma nova rodada começou, aborta essa
      setSpinDisplay(spinPool[i % spinPool.length]);
      await new Promise((res) => setTimeout(res, SPIN_INTERVALS[i]));
    }

    const r = await fetchPromise;
    if (spinRunId.current !== runId) return;
    if (!r || !r.ok) {
      setPoolError(r?.error || 'Falha ao sortear time');
      setSpinning(false);
      return;
    }

    setSpinDisplay(r.team.name);
    await new Promise((res) => setTimeout(res, 520)); // tempo do "landing" visual

    if (spinRunId.current !== runId) return;
    setTeamPool(r.team.players);
    setDrawnTeamName(r.team.name);
    setUsedTeams((prev) => (prev.includes(r.team.name) ? prev : [...prev, r.team.name]));
    setSpinning(false);
  }

  useEffect(() => {
    drawNewTeam([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eraId]);

  function reshuffleTeam() {
    if (reshuffles <= 0) return;
    setReshuffles((n) => n - 1);
    const poolNicks = new Set(teamPool.map((p) => p.nickname));
    setPicks((prev) => prev.filter((pk) => !poolNicks.has(pk.player.nickname)));
    drawNewTeam(usedTeams);
  }

  function pickPoolPlayer(idx) {
    const p = teamPool[idx];
    if (!p) return;
    // Defesa extra: mesmo que o clique já devesse estar desabilitado num
    // card "usado" (ver usedNicks/PoolCard abaixo), nunca permite que o
    // mesmo nickname ocupe dois slots — pode acontecer de um jogador
    // aparecer no elenco de mais de um time sorteado na mesma era.
    if (picks.some((pk) => pk.player.nickname === p.nickname)) return;

    const filledIdxs = new Set(picks.map((pk) => pk.slotIdx));
    const roleHint = p.role_hint || p.role || '';
    let targetSlot = ROLE_TO_SLOT[roleHint];
    if (targetSlot === undefined || filledIdxs.has(targetSlot)) {
      targetSlot = ROLE_ORDER.findIndex((_, i) => !filledIdxs.has(i));
    }
    if (targetSlot === -1 || targetSlot === undefined) return; // todos os slots preenchidos

    const slotRole = ROLE_ORDER[targetSlot];
    const nextPicks = [...picks, { slotIdx: targetSlot, player: { ...p, role: slotRole } }];
    setPicks(nextPicks);

    if (nextPicks.length < 5) {
      drawNewTeam(usedTeams);
    }
  }

  function unpickSlot(slotIdx) {
    setPicks((prev) => prev.filter((pk) => pk.slotIdx !== slotIdx));
  }

  const filledCount = picks.length;
  const canConfirm = filledCount === 5 && teamNameInput.trim().length > 0;
  const usedNicks = new Set(picks.map((pk) => pk.player.nickname));

  return (
    <div className="draft-screen">
      <div className="draft-topbar">
        <div className="draft-topbar-left">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
            Era
          </Button>
          <span className="draft-topbar-title">Monte seu Time</span>
        </div>
        <span className="draft-step-label">Passo 2 de 3</span>
      </div>

      <div className="draft-body">
        {/* ── SIDEBAR: nome do time + slots ── */}
        <div className="draft-sidebar">
          <div className="draft-name-field">
            <label className="draft-field-label" htmlFor="team-name-inp">Nome do Time</label>
            <input
              id="team-name-inp"
              className="team-name-inp"
              placeholder="Ex: FURIA, NaVi…"
              maxLength={28}
              value={teamNameInput}
              onChange={(e) => setTeamNameInput(e.target.value)}
            />
          </div>

          <div className="draft-reshuffle-block">
            <span className="draft-suggested-name">{drawnTeamName || '–'}</span>
            <Button variant="ghost" size="sm" disabled={reshuffles <= 0 || spinning} onClick={reshuffleTeam} title="Sortear outro time">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 3 21 3 21 8" /><line x1="4" y1="20" x2="21" y2="3" /><polyline points="21 16 21 21 16 21" /><line x1="15" y1="15" x2="21" y2="21" /></svg>
              Re-sortear
            </Button>
            <span className="draft-reshuffle-count">{reshuffles}×</span>
          </div>

          <div className="draft-progress-row">
            <span className="draft-section-title">Escalação</span>
            <div className="draft-progress">
              {ROLE_ORDER.map((_, i) => (
                <div key={i} className={`dp-pip ${i < filledCount ? 'done' : i === filledCount ? 'current' : ''}`} />
              ))}
            </div>
          </div>

          <div className="slot-list">
            {ROLE_ORDER.map((role, i) => {
              const pick = picks.find((pk) => pk.slotIdx === i);
              const emoji = ROLE_EMOJI[role] || '?';
              if (pick) {
                const p = pick.player;
                return (
                  <div key={i} className="slot filled">
                    <div className="slot-icon">{emoji}</div>
                    <div className="slot-info">
                      <div className="slot-role-lbl">{role}</div>
                      <div className="slot-nick">{flag(p.country)} {p.nickname}</div>
                      <div className="slot-sub">RTG {p.attributes.rating.toFixed(1)} · KPR {p.attributes.kpr?.toFixed(2) ?? '–'}</div>
                    </div>
                    <button className="slot-remove" onClick={() => unpickSlot(i)} title="Remover">✕</button>
                  </div>
                );
              }
              return (
                <div key={i} className="slot">
                  <div className="slot-icon">{emoji}</div>
                  <div className="slot-info">
                    <div className="slot-role-lbl">{role}</div>
                    <div className="slot-empty">Clique num jogador ao lado</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="draft-sidebar-footer">
            <Button variant="orange" disabled={!canConfirm} onClick={() => onConfirm({ teamName: teamNameInput.trim(), picks })}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3" /></svg>
              Continuar
            </Button>
          </div>
        </div>

        {/* ── PAINEL DIREITO: pool de jogadores do time sorteado ── */}
        <div className="draft-right-panel">
          <div className="draft-panel-header">
            <div className="draft-team-banner">
              <div className="dtb-icon">{flag(guessTeamCountry(teamPool))}</div>
              <div>
                <div className="dtb-label">Time disponível · Era {eraId}</div>
                <div className="dtb-name">{drawnTeamName || '–'}</div>
              </div>
            </div>
            <div className="draft-guide">
              <span className="draft-guide-icon">✋</span>
              <span><b>Clique</b> num jogador pra adicioná-lo automaticamente na função dele</span>
            </div>
          </div>

          <div className="draft-pool-scroll">
            {spinning && (
              <div className="draft-spin-wrap">
                <div className="draft-spin-label">Sorteando time…</div>
                <div className="draft-spin-name">{spinDisplay}</div>
              </div>
            )}
            {!spinning && poolError && (
              <div className="draft-loading" style={{ color: 'var(--color-danger)' }}>Erro: {poolError}</div>
            )}
            {!spinning && !poolError && (
              <div className="pool-grid">
                {teamPool.map((p, idx) => (
                  <PoolCard key={p.nickname + idx} player={p} used={usedNicks.has(p.nickname)} onPick={() => pickPoolPlayer(idx)} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function guessTeamCountry(pool) {
  if (!pool || !pool.length) return '';
  const counts = {};
  pool.forEach((p) => { const c = p.country || ''; counts[c] = (counts[c] || 0) + 1; });
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
}

function PoolCard({ player: p, used, onPick }) {
  const role = p.role_hint || p.role || '';
  const keyStats = new Set(KEY_STATS[role] || []);
  const attrs = p.attributes || {};
  const roleColor = ROLE_COLOR[role];

  return (
    <div className={`pool-card ${used ? 'pool-used pool-selected' : ''}`} onClick={used ? undefined : onPick}>
      <div className="pool-card-header">
        <span className="pool-flag">{flag(p.country || '')}</span>
        <div>
          <div className="pool-nick">{p.nickname || '?'}</div>
          <div className="pool-real">{p.name || ''}</div>
        </div>
      </div>
      <div className="pool-badges">
        {role && (
          <span className="pool-role-badge" style={roleColor}>
            {ROLE_EMOJI[role] || ''} {role}
          </span>
        )}
        {p.trait && <span className="pool-trait-badge">{p.trait}</span>}
      </div>
      <div className="pool-stats">
        {STAT_KEYS.map(([k, label]) => {
          const val = attrs[k];
          const isKey = keyStats.has(k);
          const formatted = val != null ? ((k === 'kast' || k === 'adr') ? Math.round(val) : val.toFixed(2)) : '–';
          return (
            <div className="ps-mini" key={k}>
              <div className={`ps-mini-v ${isKey ? 'key-stat' : ''}`}>{formatted}</div>
              <div className="ps-mini-k">{label}</div>
            </div>
          );
        })}
      </div>
      {used && <div className="pool-selected-tag">✓ Selecionado</div>}
    </div>
  );
}
