import Button from '../ui/Button';
import { STAGE_LABELS } from '../../constants/stages';
import { ROLE_EMOJI, flag } from '../../constants/roles';
import './StageModal.css';

// Port de showStageModal()/buildFeats(). Aparece quando a fase da campanha
// muda entre o início e o fim de uma partida (Stage 1 → Stage 2, Stage 2 →
// Playoffs, eliminação em qualquer fase, ou título do Major) — a Hub
// (App.jsx) decide QUANDO mostrar comparando campaign.stage antes/depois;
// esse componente só decide COMO mostrar dado o `kind` já determinado.
export default function StageModal({ kind, team, history, newStage, stageMvp, onContinue }) {
  const isChamp = kind === 'champ';
  const isElim = kind === 'elim';

  const borderCls = isChamp ? 'border-champ' : isElim ? 'border-elim' : 'border-advance';
  const titleCls = isChamp ? 'champ' : isElim ? 'elim' : 'advance';
  const title = isChamp ? '🏆 CAMPEÃO!' : isElim ? '💔 ELIMINADO' : '✅ AVANÇOU!';
  const subtitle = isChamp
    ? 'Você conquistou o Major. Lenda absoluta.'
    : isElim
      ? 'A campanha chegou ao fim. Faz parte do jogo.'
      : `Seu time garantiu a classificação! Próxima fase: ${STAGE_LABELS[newStage] || 'Próxima Fase'}`;
  const btnLabel = isChamp ? '🎉 Finalizar' : isElim ? 'Encerrar Campanha' : 'Próxima Fase →';

  const feats = buildFeats({ isChamp, isElim, team, history, stageMvp });

  return (
    <div className="stage-overlay">
      <div className={`stage-modal ${borderCls}`}>
        <div className="stm-verdict">
          <div className={`stm-title ${titleCls}`}>{title}</div>
          <div className="stm-subtitle">{subtitle}</div>
        </div>

        <div className="stm-section-label">Feitos da Campanha</div>
        <div className="stm-feats">
          {feats.map((f, i) => <div className="stm-feat" key={i} dangerouslySetInnerHTML={{ __html: f }} />)}
        </div>

        <div className="stm-section-label">Escalação</div>
        <div className="stm-roster">
          {(team?.players || []).map((p) => (
            <div className="stm-player" key={p.nickname}>
              <div className="stm-p-nick">{flag(p.country)} {p.nickname}</div>
              <div className="stm-p-role">{ROLE_EMOJI[p.role] || ''} {p.role}</div>
              <div className="stm-p-stats">
                <div className="stm-ps"><div className="stm-ps-v" style={{ color: 'var(--color-primary)' }}>{p.attributes.rating.toFixed(2)}</div><div className="stm-ps-k">RTG</div></div>
                <div className="stm-ps"><div className="stm-ps-v" style={{ color: 'var(--color-success)' }}>{p.attributes.kast.toFixed(1)}</div><div className="stm-ps-k">KAST</div></div>
                <div className="stm-ps"><div className="stm-ps-v" style={{ color: 'var(--color-danger)' }}>{p.attributes.impact.toFixed(1)}</div><div className="stm-ps-k">IMP</div></div>
              </div>
            </div>
          ))}
        </div>

        <div className="stm-footer">
          <Button variant="orange" size="lg" onClick={onContinue}>{btnLabel}</Button>
        </div>
      </div>
    </div>
  );
}

function buildFeats({ isChamp, isElim, team, history, stageMvp }) {
  const h = history || [];
  if (!h.length) return ['Nenhuma série jogada ainda.'];

  const feats = [];
  const wins = h.filter((x) => x.result === 'win').length;
  const losses = h.filter((x) => x.result === 'loss').length;
  feats.push(`📊 Resultado no stage: <b>${wins} vitórias</b> e <b>${losses} derrotas</b> em ${h.length} séries.`);

  let streak = 0;
  const streakType = h[h.length - 1]?.result;
  for (let i = h.length - 1; i >= 0 && h[i].result === streakType; i--) streak++;
  if (streak >= 2) {
    feats.push(streakType === 'win'
      ? `🔥 Sequência de <b>${streak} vitórias consecutivas</b>.`
      : `❄️ Sequência negativa de <b>${streak} derrotas consecutivas</b>.`);
  }

  if (team?.players?.length) {
    const best = [...team.players].sort((a, b) => b.attributes.rating - a.attributes.rating)[0];
    feats.push(`⭐ Destaque do time: <b>${best.nickname}</b> (RTG ${best.attributes.rating.toFixed(2)}, ${best.role}).`);
  }

  if (stageMvp) {
    const isMine = team?.players?.some((p) => p.nickname === stageMvp.nickname);
    const label = isMine ? '🏅 MVP do Stage (seu time!)' : '🏅 MVP do Stage';
    feats.push(`${label}: <b>${stageMvp.nickname}</b> (${stageMvp.team}) — ${stageMvp.kills}/${stageMvp.deaths} K/D (${stageMvp.kd.toFixed(2)}), ADR ${stageMvp.adr.toFixed(1)}, Rating ${stageMvp.rating.toFixed(3)}.`);
  }

  if (isChamp) feats.push(`🏆 <b>${team?.name}</b> conquistou o Major! Uma corrida histórica e inesquecível.`);
  if (isElim) feats.push(`💬 A jornada de <b>${team?.name}</b> terminou aqui. Mas a lenda começa a ser construída.`);

  return feats;
}
