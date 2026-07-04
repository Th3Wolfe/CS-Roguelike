import { ROLE_EMOJI, ROLE_COLOR, flag } from '../../constants/roles';
import './RosterPanel.css';

const STATS = [
  ['rating', 'RTG'],
  ['kast', 'KAST'],
  ['impact', 'IMP'],
  ['adr', 'ADR'],
  ['kpr', 'KPR'],
];

function vTier(v) {
  return v >= 8.3 ? 'v-hi' : v >= 6.8 ? 'v-mid' : 'v-lo';
}
function eColor(v) {
  return v >= 70 ? 'var(--green)' : v >= 40 ? 'var(--orange)' : 'var(--red)';
}

export default function RosterPanel({ team }) {
  const players = team?.players || [];

  return (
    <div className="players-grid">
      {players.map((p) => (
        <PlayerCard key={p.nickname} player={p} />
      ))}
    </div>
  );
}

function PlayerCard({ player: p }) {
  const a = p.attributes || {};
  const s = p.status || {};
  const phys = s.physical ?? 100;
  const ment = s.mental ?? 100;
  const roleColor = ROLE_COLOR[p.role];

  return (
    <div className="player-card">
      <div className="pc-top">
        <span className="pc-flag">{flag(p.country)}</span>
        <div className="pc-info">
          <div className="pc-nick">{p.nickname}</div>
          <div className="pc-real">{p.name}</div>
          <div className="pc-badges">
            <span className="pc-role-badge" style={roleColor}>{ROLE_EMOJI[p.role] || ''} {p.role}</span>
            {p.trait && <span className="pc-trait-badge">{p.trait}</span>}
            <span className="pc-era-badge">{p.era || '?'}</span>
          </div>
        </div>
      </div>

      <div className="pc-stats">
        {STATS.map(([k, label]) => {
          const val = a[k];
          return (
            <div className="ps-col" key={k}>
              <div className={`ps-v ${val != null ? vTier(val) : ''}`}>{val != null ? val.toFixed(2) : '–'}</div>
              <div className="ps-k">{label}</div>
            </div>
          );
        })}
      </div>

      <div className="pc-status">
        <div className="pcs-item">
          <div className="pcs-lbl">💪 Físico</div>
          <div className="pcs-bar"><div className="pcs-fill" style={{ width: `${phys}%`, background: eColor(phys) }} /></div>
          <div className="pcs-val" style={{ color: eColor(phys) }}>{Math.round(phys)}%</div>
        </div>
        <div className="pcs-item">
          <div className="pcs-lbl">🧠 Mental</div>
          <div className="pcs-bar"><div className="pcs-fill" style={{ width: `${ment}%`, background: eColor(ment) }} /></div>
          <div className="pcs-val" style={{ color: eColor(ment) }}>{Math.round(ment)}%</div>
        </div>
        <div className="pcs-item">
          <div className="pcs-lbl">😤 Moral</div>
          <div className="pcs-val" style={{ color: s.morale >= 0 ? 'var(--green)' : 'var(--red)' }}>
            {s.morale >= 0 ? '+' : ''}{(s.morale ?? 0).toFixed(1)}
          </div>
        </div>
        <div className="pcs-item">
          <div className="pcs-lbl">📈 Forma</div>
          <div className="pcs-val" style={{ color: s.form >= 0 ? 'var(--green)' : 'var(--red)' }}>
            {s.form >= 0 ? '+' : ''}{(s.form ?? 0).toFixed(1)}
          </div>
        </div>
      </div>

      {(p.buffs || []).length > 0 && (
        <div className="pc-buffs">
          {p.buffs.map((b, i) => (
            <span className="pc-buff-tag" key={i} style={{ color: b.effect >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {b.name}({b.duration})
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
