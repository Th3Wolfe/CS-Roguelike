import { useState } from 'react';
import { post } from '../../api/client';
import ShareCodePanel from '../menu/ShareCodePanel';
import { STAGE_LABELS } from '../../constants/stages';
import './HubTopbar.css';

// Os badges "Era Atual" e "Créditos" existem no vanilla mas nunca foram
// conectados a um dado real (team.credits/campaign.credits não existem em
// nenhum model do backend, e G.draft.eraId é um estado transitório da tela
// de draft, não algo que sobrevive no /api/state). Mantive os badges pra não
// quebrar o layout, mas eles mostram "–" honestamente — não inventei um
// valor falso só para preencher.
export default function HubTopbar({ team, campaign, onBackToMenu }) {
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const [showShare, setShowShare] = useState(false);

  async function handleSave() {
    setSaving(true);
    setSaveMsg(null);
    try {
      const r = await post('/api/save');
      setSaveMsg(r.ok ? 'Salvo!' : (r.error || 'Erro ao salvar'));
    } catch (err) {
      setSaveMsg(err.message);
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(null), 2500);
    }
  }

  function handleMenuClick() {
    if (window.confirm('Voltar ao menu?')) onBackToMenu();
  }

  const stageLabel = STAGE_LABELS[campaign?.stage] || campaign?.stage || '–';

  return (
    <>
      <div className="game-topbar">
        <div className="gtb-left">
          <div className="hud-logo">
            <svg className="hud-logo-mark" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <polygon points="16,2 30,9 30,23 16,30 2,23 2,9" fill="#0B1016" stroke="#F6B333" strokeWidth="1.5" />
              <polygon points="16,7 25,12 25,21 16,26 7,21 7,12" fill="rgba(246,179,51,.1)" stroke="#F6B333" strokeWidth="1" />
              <text x="16" y="21" textAnchor="middle" fontFamily="'Barlow Condensed',sans-serif" fontWeight="900" fontSize="11" fill="#F6B333">CS</text>
            </svg>
            <div className="hud-logo-text">
              <span className="hud-logo-top">Hub</span>
              <span className="hud-logo-sub">CS Manager</span>
            </div>
          </div>
          <div className="hud-divider" />
          <span className="team-title">{team?.name || '–'}</span>
          <span className="stage-chip">{stageLabel}</span>
        </div>

        <div className="hud-status">
          <div className="hud-badge">
            <span className="hud-badge-label">Era Atual</span>
            <span className="hud-badge-value">–</span>
          </div>
          <div className="hud-divider" />
          <div className="hud-badge">
            <span className="hud-badge-label">Créditos</span>
            <span className="hud-badge-value success">–</span>
          </div>
        </div>

        <div className="gtb-right">
          {saveMsg && <span style={{ fontSize: '.72rem', color: 'var(--text2)', marginRight: 6 }}>{saveMsg}</span>}
          <button className="btn btn-ghost btn-sm" onClick={handleSave} disabled={saving} title="Salvar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" /></svg>
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowShare(true)} title="Compartilhar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" /></svg>
          </button>
          <button className="btn btn-ghost btn-sm" onClick={handleMenuClick} title="Menu">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
      </div>

      {showShare && <ShareCodePanel onClose={() => setShowShare(false)} />}
    </>
  );
}
