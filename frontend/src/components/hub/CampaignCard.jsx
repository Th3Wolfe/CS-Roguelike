import { STAGE_LABELS, STAGE_FORMATS } from '../../constants/stages';
import './hub.css';

const DOTS_PER_STAGE = 5; // Swiss é "3V ou 3D", mas a trilha sempre mostra 5 slots

export default function CampaignCard({ campaign }) {
  const stage = campaign?.stage;
  const label = STAGE_LABELS[stage] || stage || '–';
  const format = STAGE_FORMATS[stage] || '';

  const stageStats = campaign?.[stage]; // { wins, losses } em stage1/stage2
  const wins = stageStats?.wins ?? 0;
  const losses = stageStats?.losses ?? 0;

  const history = campaign?.history || [];
  const stageHistory = history.filter((h) => h.stage === stage);
  const emptySlots = Math.max(0, DOTS_PER_STAGE - stageHistory.length);

  return (
    <div className="hub-info-card">
      <div className="hub-ic-label">Campanha Atual</div>
      <div className="hub-ic-stage">{label}</div>
      <div className="hub-ic-sub">{format}</div>
      <div className="hub-ic-wl">
        <b>{wins}</b>W / <b>{losses}</b>L
      </div>
      <div className="hub-wl-track">
        {stageHistory.map((h, i) => (
          <div key={i} className={`hub-wl-dot ${h.result === 'win' ? 'w' : 'l'}`} />
        ))}
        {Array.from({ length: emptySlots }).map((_, i) => (
          <div key={`empty-${i}`} className="hub-wl-dot" />
        ))}
      </div>
    </div>
  );
}
