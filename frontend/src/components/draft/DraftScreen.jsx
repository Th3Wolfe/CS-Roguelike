import { useEffect, useRef, useState } from 'react';
import { post } from '../../api/client';
import Button from '../ui/Button';
import {
  ROLE_ORDER, ROLE_EMOJI, ROLE_COLOR, KEY_STATS, STAT_KEYS, flag, SPIN_TEAM_NAMES,
} from '../../constants/roles';
import './DraftScreen.css';

const SPIN_INTERVALS = [50, 55, 60, 70, 80, 100, 120, 150, 180, 220, 270, 320];
const ROLE_TO_SLOT = Object.fromEntries(ROLE_ORDER.map((r, i) => [r, i]));
const DRAG_THRESHOLD = 6; // px de movimento antes de virar "arrastar" (em vez de clique)
const LAND_ANIM_MS = 480; // duração do brilho de "pouso" no slot

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

  // ── Drag & drop (pointer events, funciona com mouse e touch) ──
  const [dragGhost, setDragGhost] = useState(null); // { x, y, kind: 'pool'|'slot', player, payload } enquanto arrasta de fato
  const [dragOverSlot, setDragOverSlot] = useState(null); // slotIdx sob o ponteiro
  const [justFilledSlot, setJustFilledSlot] = useState(null); // slotIdx que acabou de "pousar"
  const dragState = useRef({ active: false, moved: false, startX: 0, startY: 0, payload: null });
  const suppressNextClick = useRef(false);
  const landTimeout = useRef(null);

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

  useEffect(() => () => clearTimeout(landTimeout.current), []);

  function triggerLandAnim(slotIdx) {
    setJustFilledSlot(slotIdx);
    clearTimeout(landTimeout.current);
    landTimeout.current = setTimeout(() => setJustFilledSlot(null), LAND_ANIM_MS);
  }

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
    triggerLandAnim(targetSlot);

    if (nextPicks.length < 5) {
      drawNewTeam(usedTeams);
    }
  }

  // Arrasta um jogador do pool direto pro slot escolhido (em vez do
  // auto-assign por role_hint). Se o slot alvo já tiver alguém, essa
  // pessoa sai do time (fica pra fora, como se tivesse sido removida).
  function dropPoolPlayerOnSlot(poolIdx, targetSlot) {
    const p = teamPool[poolIdx];
    if (!p) return;
    if (picks.some((pk) => pk.player.nickname === p.nickname)) return;

    const wasFilled = picks.some((pk) => pk.slotIdx === targetSlot);
    const slotRole = ROLE_ORDER[targetSlot];
    setPicks((prev) => [
      ...prev.filter((pk) => pk.slotIdx !== targetSlot),
      { slotIdx: targetSlot, player: { ...p, role: slotRole } },
    ]);
    triggerLandAnim(targetSlot);

    if (!wasFilled && picks.length + 1 < 5) {
      drawNewTeam(usedTeams);
    }
  }

  // Arrasta um jogador já escalado pra outro slot — troca de posição
  // (e de role) com quem estiver lá, ou só move se o destino tiver vazio.
  function reorderSlots(fromIdx, toIdx) {
    if (fromIdx === toIdx) return;
    setPicks((prev) => {
      const fromPick = prev.find((pk) => pk.slotIdx === fromIdx);
      if (!fromPick) return prev;
      const toPick = prev.find((pk) => pk.slotIdx === toIdx);
      const next = prev.filter((pk) => pk.slotIdx !== fromIdx && pk.slotIdx !== toIdx);
      next.push({ slotIdx: toIdx, player: { ...fromPick.player, role: ROLE_ORDER[toIdx] } });
      if (toPick) {
        next.push({ slotIdx: fromIdx, player: { ...toPick.player, role: ROLE_ORDER[fromIdx] } });
      }
      return next;
    });
    triggerLandAnim(toIdx);
  }

  function unpickSlot(slotIdx) {
    setPicks((prev) => prev.filter((pk) => pk.slotIdx !== slotIdx));
  }

  function handleDragStart(e, payload) {
    if (e.button !== undefined && e.button !== 0) return; // só botão principal / touch
    if (e.target.closest('.slot-remove')) return; // não inicia drag pelo botão de remover
    e.currentTarget.setPointerCapture(e.pointerId);
    dragState.current = {
      active: true, moved: false, startX: e.clientX, startY: e.clientY, payload,
    };
  }

  function handleDragMove(e) {
    const st = dragState.current;
    if (!st.active) return;
    const dx = e.clientX - st.startX;
    const dy = e.clientY - st.startY;

    if (!st.moved && Math.hypot(dx, dy) > DRAG_THRESHOLD) {
      st.moved = true;
      setDragGhost({ x: e.clientX, y: e.clientY, ...buildGhostData(st.payload) });
    }
    if (st.moved) {
      setDragGhost((g) => (g ? { ...g, x: e.clientX, y: e.clientY } : g));
      const el = document.elementFromPoint(e.clientX, e.clientY);
      const slotEl = el && el.closest('[data-slot-idx]');
      setDragOverSlot(slotEl ? Number(slotEl.dataset.slotIdx) : null);
    }
  }

  function handleDragEnd() {
    const st = dragState.current;
    if (st.active && st.moved) {
      suppressNextClick.current = true;
      if (dragOverSlot !== null) {
        if (st.payload.source === 'pool') {
          dropPoolPlayerOnSlot(st.payload.poolIdx, dragOverSlot);
        } else if (st.payload.source === 'slot') {
          reorderSlots(st.payload.slotIdx, dragOverSlot);
        }
      }
    }
    dragState.current = { active: false, moved: false, startX: 0, startY: 0, payload: null };
    setDragGhost(null);
    setDragOverSlot(null);
  }

  function buildGhostData(payload) {
    if (payload.source === 'pool') {
      return { kind: 'pool', player: teamPool[payload.poolIdx], payload };
    }
    const pk = picks.find((x) => x.slotIdx === payload.slotIdx);
    return { kind: 'slot', player: pk?.player, payload };
  }

  const filledCount = picks.length;
  const canConfirm = filledCount === 5 && teamNameInput.trim().length > 0;
  const usedNicks = new Set(picks.map((pk) => pk.player.nickname));
  const draggingPayload = dragGhost?.payload;

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
              autoComplete="off"
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
              const slotClasses = [
                'slot',
                pick ? 'filled' : '',
                dragOverSlot === i ? 'drag-over' : '',
                justFilledSlot === i ? 'slot-landed' : '',
                draggingPayload?.source === 'slot' && draggingPayload.slotIdx === i ? 'is-drag-source' : '',
              ].filter(Boolean).join(' ');

              if (pick) {
                const p = pick.player;
                return (
                  <div
                    key={i}
                    data-slot-idx={i}
                    className={slotClasses}
                    onPointerDown={(e) => handleDragStart(e, { source: 'slot', slotIdx: i })}
                    onPointerMove={handleDragMove}
                    onPointerUp={handleDragEnd}
                    onPointerCancel={handleDragEnd}
                    title="Arraste pra trocar de posição"
                  >
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
                <div key={i} data-slot-idx={i} className={slotClasses}>
                  <div className="slot-icon">{emoji}</div>
                  <div className="slot-info">
                    <div className="slot-role-lbl">{role}</div>
                    <div className="slot-empty">Clique ou arraste um jogador ao lado</div>
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
              <span><b>Clique</b> num jogador pra adicioná-lo automaticamente na função dele, ou <b>arraste</b> pra escolher a posição</span>
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
                  <PoolCard
                    key={p.nickname + idx}
                    player={p}
                    used={usedNicks.has(p.nickname)}
                    isDragSource={draggingPayload?.source === 'pool' && draggingPayload.poolIdx === idx}
                    onPick={() => {
                      if (suppressNextClick.current) { suppressNextClick.current = false; return; }
                      pickPoolPlayer(idx);
                    }}
                    onDragStart={(e) => handleDragStart(e, { source: 'pool', poolIdx: idx })}
                    onDragMove={handleDragMove}
                    onDragEnd={handleDragEnd}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {dragGhost && dragGhost.player && (
        <div className={`drag-ghost drag-ghost-${dragGhost.kind}`} style={{ left: dragGhost.x, top: dragGhost.y }}>
          {dragGhost.kind === 'pool' ? (
            <PoolCard player={dragGhost.player} used={false} isDragSource={false} onPick={() => {}} />
          ) : (
            <div className="slot filled drag-ghost-slot-inner">
              <div className="slot-icon">{ROLE_EMOJI[dragGhost.player.role] || '?'}</div>
              <div className="slot-info">
                <div className="slot-role-lbl">{dragGhost.player.role}</div>
                <div className="slot-nick">{flag(dragGhost.player.country)} {dragGhost.player.nickname}</div>
                <div className="slot-sub">RTG {dragGhost.player.attributes.rating.toFixed(1)} · KPR {dragGhost.player.attributes.kpr?.toFixed(2) ?? '–'}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function guessTeamCountry(pool) {
  if (!pool || !pool.length) return '';
  const counts = {};
  pool.forEach((p) => { const c = p.country || ''; counts[c] = (counts[c] || 0) + 1; });
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
}

function PoolCard({ player: p, used, isDragSource, onPick, onDragStart, onDragMove, onDragEnd }) {
  const role = p.role_hint || p.role || '';
  const keyStats = new Set(KEY_STATS[role] || []);
  const attrs = p.attributes || {};
  const roleColor = ROLE_COLOR[role];

  return (
    <div
      className={`pool-card ${used ? 'pool-used pool-selected' : ''} ${isDragSource ? 'is-drag-source' : ''}`}
      onClick={used ? undefined : onPick}
      onPointerDown={used ? undefined : onDragStart}
      onPointerMove={used ? undefined : onDragMove}
      onPointerUp={used ? undefined : onDragEnd}
      onPointerCancel={used ? undefined : onDragEnd}
    >
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
