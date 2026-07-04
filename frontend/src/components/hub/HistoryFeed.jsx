import { STAGE_LABELS } from '../../constants/stages';
import './WelcomeAndHistory.css';

const STAGE_ABBR = {
  stage1: 'S1', stage2: 'S2',
  playoffs_qf: 'QF', playoffs_sf: 'SF', playoffs_final: 'GF',
};

export default function HistoryFeed({ history }) {
  const items = [...(history || [])].reverse().slice(0, 20);

  return (
    <div className="hub-history">
      <div className="hub-history-title">Histórico de Partidas</div>
      <div className="hist-feed">
        {items.length === 0 && <div className="hf-empty">Nenhuma série jogada ainda.</div>}
        {items.map((h, i) => (
          <div className="hf-item" key={i}>
            <span className={`hf-badge ${h.result === 'win' ? 'w' : 'l'}`}>{h.result === 'win' ? 'W' : 'L'}</span>
            <span className="hf-opp">vs {h.opponent_name}</span>
            <span className="hf-stage" title={STAGE_LABELS[h.stage] || h.stage}>{STAGE_ABBR[h.stage] || h.stage}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
