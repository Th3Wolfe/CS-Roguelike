import { getNextOpponentInfo } from '../../utils/nextOpponent';
import { isStageFinished } from '../../constants/stages';
import TeamShield from './TeamShield';
import './hub.css';

// Migração do card que estava quebrado no vanilla (ui/index.html nunca
// escrevia nesses elementos — ver correção anterior em getNextOpponentInfo /
// updateNextMatchupCard). Aqui o mesmo cálculo vira dado real de render,
// então não tem como esse card voltar a ficar "congelado".
export default function NextMatchupCard({ team, campaign, bracket }) {
  const finished = isStageFinished(campaign?.stage);
  const oppInfo = finished ? null : getNextOpponentInfo({ campaign, team, bracket });

  let label, sub;
  if (oppInfo) {
    label = oppInfo.name;
    sub = oppInfo.strength != null
      ? `${oppInfo.stageLabel} · Força ${oppInfo.strength.toFixed(1)}`
      : (oppInfo.stageLabel || '');
  } else if (finished) {
    label = campaign?.stage === 'finished_win' ? 'Campanha concluída' : 'Eliminado';
    sub = '';
  } else {
    label = 'Aguardando adversário';
    sub = 'Próxima rodada em breve.';
  }

  return (
    <div className="hub-info-card">
      <div className="hub-ic-label">Próxima Partida</div>
      <div className="hub-ic-matchup">
        <TeamShield teamName={team?.name} fallback="🛡️" />
        <div className="hub-ic-vs">VS</div>
        <TeamShield teamName={oppInfo?.name} fallback="🦅" />
      </div>
      <div className="hub-ic-waiting">{label}</div>
      <div style={{ fontSize: '.7rem', color: 'var(--text3)', marginTop: 4 }}>{sub}</div>
    </div>
  );
}
