import { useState } from 'react';
import './BracketPanel.css';

// Port fiel do sistema de bracket "fold" do vanilla (renderBracket,
// renderSwissBracket, renderPlayoffBracket, bkMatchCard) — reconstrói os
// confrontos rodada-a-rodada a partir do histórico de TODOS os times
// (jogador + NPCs), já que o backend não expõe uma tabela de rodadas pronta.
const STAGE_ORDER = ['stage1', 'stage2', 'playoffs_qf', 'playoffs_sf', 'playoffs_final', 'finished_win', 'finished_loss'];

function truncateTeam(name, maxLen = 13) {
  if (!name) return '?';
  return name.length > maxLen ? name.slice(0, maxLen) + '…' : name;
}

export default function BracketPanel({ team, campaign, bracket }) {
  const playerName = team?.name;
  const history = campaign?.history || [];
  const stg = campaign?.stage;
  const npcTeams = bracket?.npc_teams || [];
  const pendingPairings = bracket?.pending_pairings || [];

  const s1h = history.filter((h) => h.stage === 'stage1');
  const s2h = history.filter((h) => h.stage === 'stage2');

  const stgIdx = STAGE_ORDER.indexOf(stg);
  const s1Current = stg === 'stage1';
  const s1Done = stgIdx > 0;
  const s2Current = stg === 'stage2';
  const s2Done = stgIdx > 1;
  const poStarted = stgIdx >= 2;
  const poCurrent = stgIdx >= 2 && stgIdx <= 4;

  const s1Wins = campaign?.stage1?.wins ?? 0;
  const s1Loss = campaign?.stage1?.losses ?? 0;
  const s2Wins = campaign?.stage2?.wins ?? 0;
  const s2Loss = campaign?.stage2?.losses ?? 0;
  const s1Elim = s1Done && s1Wins < 3;
  const s2Elim = s2Done && s2Wins < 3;

  return (
    <div>
      <StageFold
        title="Stage 1"
        pill={<StagePill wins={s1Wins} losses={s1Loss} isCurrent={s1Current} isDone={s1Done} wasElim={s1Elim} />}
        defaultOpen={s1Current || !s1Done}
        isCurrent={s1Current}
      >
        <SwissBracket
          playerHistory={s1h} playerRecord={campaign?.stage1} npcTeams={npcTeams}
          pendingPairings={pendingPairings} fieldPrefix="s1"
          isCurrent={s1Current} isDone={s1Done} isLocked={false} playerName={playerName}
        />
      </StageFold>

      <StageFold
        title="Stage 2"
        pill={<StagePill wins={s2Wins} losses={s2Loss} isCurrent={s2Current} isDone={s2Done} wasElim={s2Elim} />}
        defaultOpen={s2Current}
        isCurrent={s2Current}
      >
        <SwissBracket
          playerHistory={s2h} playerRecord={campaign?.stage2} npcTeams={npcTeams}
          pendingPairings={pendingPairings} fieldPrefix="s2"
          isCurrent={s2Current} isDone={s2Done} isLocked={stgIdx < 1} playerName={playerName}
        />
      </StageFold>

      <StageFold
        title="Playoffs"
        pill={<PlayoffPill poStarted={poStarted} stg={stg} />}
        defaultOpen={poCurrent}
        isCurrent={poCurrent}
      >
        <PlayoffBracket bracket={bracket} stg={stg} playerName={playerName} poStarted={poStarted} />
      </StageFold>

      <div className="bk-legend" style={{ marginTop: 14 }}>
        <div className="bk-leg-item"><div className="bk-leg-dot bkl-win" />Vitória</div>
        <div className="bk-leg-item"><div className="bk-leg-dot bkl-loss" />Derrota</div>
        <div className="bk-leg-item"><div className="bk-leg-dot bkl-you" />Seu time</div>
        <div className="bk-leg-item"><div className="bk-leg-dot bkl-emp" />Pendente</div>
      </div>
    </div>
  );
}

function StagePill({ wins, losses, isCurrent, isDone, wasElim }) {
  if (!isDone && !isCurrent) return <span className="br-pill brp-locked">Bloqueado</span>;
  if (isDone && !wasElim) return <span className="br-pill brp-done">✓ Avançou {wins}–{losses}</span>;
  if (isDone && wasElim) return <span className="br-pill brp-elim">✗ Eliminado {wins}–{losses}</span>;
  return <span className="br-pill brp-current">{wins}W – {losses}L</span>;
}

function PlayoffPill({ poStarted, stg }) {
  if (!poStarted) return <span className="br-pill brp-locked">Bloqueado</span>;
  if (stg === 'finished_win') return <span className="br-pill brp-done">🏆 Campeão!</span>;
  if (stg === 'finished_loss') return <span className="br-pill brp-elim">Eliminado</span>;
  return <span className="br-pill brp-current">Em curso</span>;
}

function StageFold({ title, pill, defaultOpen, isCurrent, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`stage-fold ${open ? 'open' : ''} ${isCurrent ? 'current' : ''}`} style={{ marginBottom: 8 }}>
      <div className="stage-fold-header" onClick={() => setOpen((v) => !v)}>
        <div className="stage-fold-title">{title}</div>
        {pill}
        <div className="stage-fold-chevron">▼</div>
      </div>
      <div className="stage-fold-body">{children}</div>
    </div>
  );
}

// ── Swiss bracket: reconstrói os confrontos rodada-a-rodada a partir do
// histórico de todos os times (jogador + NPCs), agrupando por "bucket" de
// recorde (ex: "2-0", "1-1", "0-2") dentro de cada rodada. ──
function SwissBracket({ playerHistory, playerRecord, npcTeams, pendingPairings, fieldPrefix, isCurrent, isDone, isLocked, playerName }) {
  const wins = playerRecord?.wins ?? 0;
  const losses = playerRecord?.losses ?? 0;

  if (isLocked) {
    return <div style={{ color: 'var(--text3)', fontSize: '.85rem', opacity: .5, padding: '10px 0' }}>Fase ainda não iniciada.</div>;
  }

  const allTeamHist = [];
  allTeamHist.push({
    name: playerName,
    hist: playerHistory.map((h) => ({
      wins_before: h.wins_before ?? 0, losses_before: h.losses_before ?? 0,
      opponent: h.opponent_name || h.opponent, result: h.result,
    })),
  });
  for (const t of npcTeams) {
    const hist = fieldPrefix === 's1' ? (t.s1_history || []) : (t.s2_history || []);
    if (fieldPrefix === 's2' && !t.advanced_s1) continue;
    allTeamHist.push({ name: t.name, hist });
  }

  const seen = new Set();
  const roundBuckets = [{}, {}, {}, {}, {}];
  for (const { name, hist } of allTeamHist) {
    for (const h of hist) {
      const ri = Math.min((h.wins_before || 0) + (h.losses_before || 0), 4);
      const bucketKey = `${h.wins_before || 0}-${h.losses_before || 0}`;
      const pairKey = ri + '|' + [name, h.opponent].sort().join('~');
      if (seen.has(pairKey)) continue;
      seen.add(pairKey);
      const won = h.result === 'win';
      const teamA = won ? name : h.opponent;
      const teamB = won ? h.opponent : name;
      if (!roundBuckets[ri][bucketKey]) roundBuckets[ri][bucketKey] = [];
      roundBuckets[ri][bucketKey].push({ a: teamA, b: teamB, winner: teamA });
    }
  }

  const ROUND_LABELS = ['Rodada 1', 'Rodada 2', 'Rodada 3', 'Rodada 4', 'Rodada 5'];
  const currentRound = isCurrent ? Math.min(wins + losses, 4) : -1;

  function sortBucketKeys(keys) {
    return keys.sort((a, b) => {
      const [aw, al] = a.split('-').map(Number);
      const [bw, bl] = b.split('-').map(Number);
      if (bw !== aw) return bw - aw;
      return al - bl;
    });
  }

  const columns = [];
  for (let ri = 0; ri < 5; ri++) {
    const buckets = roundBuckets[ri];
    const bucketKeys = sortBucketKeys(Object.keys(buckets));

    const pendingBuckets = {};
    if (isCurrent && ri === currentRound) {
      for (const p of pendingPairings) {
        const [pw, pl] = Array.isArray(p.record) ? p.record : [p.record?.[0] ?? wins, p.record?.[1] ?? losses];
        const bk = `${pw}-${pl}`;
        if (!pendingBuckets[bk]) pendingBuckets[bk] = [];
        pendingBuckets[bk].push(p);
      }
    }

    const allBucketKeys = sortBucketKeys([...new Set([...bucketKeys, ...Object.keys(pendingBuckets)])]);
    const bucketEls = [];

    if (allBucketKeys.length === 0 && ri === currentRound) {
      bucketEls.push(
        <div className="bk-bucket" key="pending-slot">
          <div className="bk-bucket-head bbh-now">{wins}–{losses}</div>
          <div className="bk-bucket-row bbr-you">
            <div className="bk-bucket-team bbt-you">{truncateTeam(playerName, 14)}</div>
            <div className="bk-bucket-vs">vs</div>
            <div className="bk-bucket-pending">a definir</div>
          </div>
        </div>
      );
    } else {
      for (const bk of allBucketKeys) {
        const matches = buckets[bk] || [];
        const pending = pendingBuckets[bk] || [];
        const isNowBucket = isCurrent && ri === currentRound;

        const rows = matches.map((m, i) => {
          const aYou = m.a === playerName, bYou = m.b === playerName;
          return (
            <div className={`bk-bucket-row ${aYou || bYou ? 'bbr-you' : ''}`} key={`m${i}`}>
              <div className={`bk-bucket-team ${aYou ? 'bbt-you' : 'bbt-win'}`}>{truncateTeam(m.a, 14)}</div>
              <div className="bk-bucket-score">W</div>
              <div className={`bk-bucket-team ${bYou ? 'bbt-you' : 'bbt-loss'}`} style={{ textAlign: 'right' }}>{truncateTeam(m.b, 14)}</div>
            </div>
          );
        });

        if (isNowBucket && pending.length > 0) {
          const playedPairs = new Set(matches.map((m) => [m.a, m.b].sort().join('~')));
          pending.forEach((p, i) => {
            const pairKey = [p.a, p.b].sort().join('~');
            if (playedPairs.has(pairKey)) return;
            const aYou = p.a === playerName, bYou = p.b === playerName;
            rows.push(
              <div className={`bk-bucket-row ${aYou || bYou ? 'bbr-you' : ''}`} key={`p${i}`}>
                <div className={`bk-bucket-team ${aYou ? 'bbt-you' : ''}`}>{truncateTeam(p.a, 14)}</div>
                <div className="bk-bucket-vs">vs</div>
                <div className={`bk-bucket-team ${bYou ? 'bbt-you' : ''}`} style={{ textAlign: 'right' }}>{truncateTeam(p.b, 14)}</div>
              </div>
            );
          });
        }

        if (rows.length === 0) continue;
        bucketEls.push(
          <div className="bk-bucket" key={bk}>
            <div className={`bk-bucket-head ${isNowBucket && bk === `${wins}-${losses}` ? 'bbh-now' : ''}`}>{bk}</div>
            {rows}
          </div>
        );
      }
    }

    columns.push(
      <div className="bk-round-col" key={ri}>
        <div className={`bk-col-head ${ri === currentRound ? 'bkh-now' : ''}`}>{ROUND_LABELS[ri]}</div>
        {bucketEls}
      </div>
    );
    if (ri < 4) columns.push(<div className="bk-round-sep" key={`sep${ri}`} />);
  }

  const advanced = [], eliminated = [];
  for (const { name } of allTeamHist) {
    const isPlayer = name === playerName;
    let w, l, done, adv;
    if (isPlayer) {
      w = wins; l = losses; done = isDone; adv = wins >= 3;
    } else {
      const t = npcTeams.find((t) => t.name === name);
      if (!t) continue;
      w = fieldPrefix === 's1' ? t.s1_wins : t.s2_wins;
      l = fieldPrefix === 's1' ? t.s1_losses : t.s2_losses;
      done = fieldPrefix === 's1' ? t.s1_done : t.s2_done;
      adv = fieldPrefix === 's1' ? t.advanced_s1 : t.advanced_s2;
    }
    if (done && adv) advanced.push(name);
    else if (done && !adv) eliminated.push(name);
  }

  return (
    <>
      <div className="bk-wrap"><div className="bk-grid">{columns}</div></div>
      {(advanced.length > 0 || eliminated.length > 0) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 18 }}>
          {advanced.length > 0 && (
            <div className="bk-result-strip brs-adv">
              <div className="bk-result-label">Avançaram</div>
              <div className="bk-result-teams">{advanced.map((n) => <Chip key={n} name={n} playerName={playerName} />)}</div>
            </div>
          )}
          {eliminated.length > 0 && (
            <div className="bk-result-strip brs-elim">
              <div className="bk-result-label">Eliminados</div>
              <div className="bk-result-teams">{eliminated.map((n) => <Chip key={n} name={n} playerName={playerName} />)}</div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

function Chip({ name, playerName }) {
  return <span className={`bk-result-chip ${name === playerName ? 'brc-you' : ''}`}>{truncateTeam(name, 16)}</span>;
}

function PlayoffBracket({ bracket, stg, playerName, poStarted }) {
  const pb = bracket?.playoff_bracket || {};
  const qfList = pb.qf || [];
  const sfList = pb.sf || [];
  const finalM = pb.final || null;
  const champ = pb.champion || null;

  const qfMatches = qfList.length ? qfList : [null, null, null, null];
  const sfMatches = sfList.length ? sfList : [null, null];

  return (
    <div className={`bk-wrap ${!poStarted ? 'bk-wrap-locked' : ''}`}>
      <div className="bk-grid">
        <div className="bk-col">
          <div className="bk-col-head">Quartas de Final</div>
          {qfMatches.map((m, i) => <MatchCard key={i} match={m} isNowStage={stg === 'playoffs_qf'} playerName={playerName} />)}
        </div>
        <div className="bk-connector"><div className="bk-connector-line" /></div>
        <div className="bk-col">
          <div className="bk-col-head">Semifinal</div>
          {sfMatches.map((m, i) => <MatchCard key={i} match={m} isNowStage={stg === 'playoffs_sf'} playerName={playerName} />)}
        </div>
        <div className="bk-connector"><div className="bk-connector-line" /></div>
        <div className="bk-col">
          <div className="bk-col-head bkh-final">Grande Final</div>
          <MatchCard match={finalM} isNowStage={stg === 'playoffs_final'} playerName={playerName} />
          {champ
            ? (
              <div className="bk-champion">
                <div className="bk-champ-trophy">🏆</div>
                <div className="bk-champ-name">{champ}</div>
                <div className="bk-champ-label">Campeão</div>
              </div>
            )
            : <div className="bk-champion bk-champ-locked"><div className="bk-champ-trophy">🏆</div></div>}
        </div>
      </div>
    </div>
  );
}

function MatchCard({ match, isNowStage, playerName }) {
  if (!match || (!match.a && !match.b)) {
    return (
      <div className="bk-match bkm-empty">
        <div className="bk-team"><div className="bk-team-name bkt-empty">–</div></div>
        <div className="bk-team"><div className="bk-team-name bkt-empty">–</div></div>
      </div>
    );
  }

  const done = !!match.winner;
  const isCur = !done && isNowStage && match.is_player_match;
  const aWon = done && match.winner === match.a;
  const bWon = done && match.winner === match.b;
  const cls = isCur ? 'bkm-current' : (done ? '' : 'bkm-empty');

  return (
    <div className={`bk-match ${cls}`}>
      <div className={`bk-team ${done ? (aWon ? 'bkt-winner' : 'bkt-loser') : ''}`}>
        <div className={`bk-team-name ${match.a === playerName ? 'bkt-you' : ''}`}>{truncateTeam(match.a, 16)}</div>
        {done ? <span className={`bk-res ${aWon ? 'bkr-win' : 'bkr-loss'}`}>{aWon ? 'W' : 'L'}</span> : <span className="bk-res bkr-vs">BO3</span>}
      </div>
      <div className={`bk-team ${done ? (bWon ? 'bkt-winner' : 'bkt-loser') : ''}`}>
        <div className={`bk-team-name ${match.b === playerName ? 'bkt-you' : ''}`}>{truncateTeam(match.b || '', 16)}</div>
        {done && <span className={`bk-res ${bWon ? 'bkr-win' : 'bkr-loss'}`}>{bWon ? 'W' : 'L'}</span>}
      </div>
    </div>
  );
}
