import { useEffect, useState } from 'react';
import { get } from '../../api/client';
import Button from '../ui/Button';
import { edgeFor, cleanTacticLabel as cleanLabel, tacticEmoji as emojiOf } from '../../utils/tacticEdge';
import './TacticsPanel.css';

// Port do hub-get-ready. A seção "Bom contra / Fraco contra" do preview
// ERA morta no vanilla (os campos que ela lia — `flavor`, `counters`,
// `weak` — nunca existiram no backend). Agora ela mostra dado real: puxamos
// a matriz de contra-ataque de /api/tactics_info (systems/tactics.py,
// CT_MATCHUP_MOD) e calculamos, pra cada tática, como ela se sai contra
// as 3 respostas possíveis do adversário do outro lado — informação de
// verdade pro jogador decidir, não só flavor text.
const TAC_MAP_IMG = {
  aggressive: '/ui/static/map-ct-agressivo.png',
  passive: '/ui/static/map-ct-passivo-hold.png',
  retake: '/ui/static/map-ct-retake.png',
  fast_rush: '/ui/static/map-tr-fastrush-execute.png',
  slow_default: '/ui/static/map-tr-slowdefault.png',
  anti_eco: '/ui/static/map-tr-antieco-push.png',
};

export default function TacticsPanel({
  selectedCT, selectedT, onSelectCT, onSelectT, onPlay, disabled,
  eyebrow = 'Antes de entrar em quadra',
  title = '⚔️ Defina seu plano de jogo para a próxima partida',
  subtitle = 'Escolha uma tática para cada lado. Isso afeta como seu time vai jogar — tente combinações diferentes ao longo da campanha.',
  footerTip = <>Você tem <b>&nbsp;1 pause técnico&nbsp;</b> por partida para rever CT e TR.</>,
  playLabel = 'Iniciar Partida',
}) {
  const [ctTactics, setCtTactics] = useState(null);
  const [tTactics, setTTactics] = useState(null);
  const [matchups, setMatchups] = useState(null);
  const [aiHint, setAiHint] = useState('');
  const [preview, setPreview] = useState(null); // { side, key }

  useEffect(() => {
    get('/api/tactics_info').then((r) => {
      if (!r.ok) return;
      setCtTactics(r.ct_tactics);
      setTTactics(r.t_tactics);
      setMatchups(r.matchups);
      setAiHint(r.ai_hint || '');
    });
  }, []);

  useEffect(() => {
    if (!preview) {
      if (selectedCT) setPreview({ side: 'ct', key: selectedCT });
      else if (selectedT) setPreview({ side: 't', key: selectedT });
    }
  }, [selectedCT, selectedT, preview]);

  const canPlay = !!selectedCT && !!selectedT && !disabled;

  return (
    <div className="hub-get-ready">
      <div className="hub-gr-head">
        <div className="hub-gr-eyebrow">{eyebrow}</div>
        <div className="hub-gr-title">{title}</div>
        <div className="hub-gr-subtitle">{subtitle}</div>
        {aiHint && (
          <div className="hub-gr-scouting">
            <span className="hub-gr-scouting-icon">🔍</span>
            <span><b>Scouting:</b> {aiHint}</span>
          </div>
        )}
      </div>

      <div className="hub-gr-body">
        <div className="hub-gr-col hub-gr-col-ct">
          <div className="hub-gr-col-header">
            <span className="hub-gr-badge hub-gr-badge-ct">CT</span>
            <div>
              <div className="hub-gr-col-name">Defesa do Site</div>
              <div className="hub-gr-col-hint">Impedir o plantio da bomba</div>
            </div>
          </div>
          <div className="hub-tac-cards">
            {ctTactics && Object.entries(ctTactics).map(([key, v]) => (
              <TacticOption
                key={key} side="ct" tacKey={key} v={v}
                selected={key === selectedCT}
                onSelect={() => { onSelectCT(key); setPreview({ side: 'ct', key }); }}
                onHover={() => setPreview({ side: 'ct', key })}
              />
            ))}
          </div>
        </div>

        <div className="hub-gr-preview">
          {!preview ? (
            <div className="hub-preview-empty">
              <div className="hub-preview-empty-icon">🗺️</div>
              <div>Clique em uma tática<br />para ver os detalhes</div>
            </div>
          ) : (
            <PreviewContent
              side={preview.side} tacKey={preview.key}
              tactics={preview.side === 'ct' ? ctTactics : tTactics}
              oppTactics={preview.side === 'ct' ? tTactics : ctTactics}
              matchups={matchups}
            />
          )}
        </div>

        <div className="hub-gr-col hub-gr-col-t">
          <div className="hub-gr-col-header">
            <span className="hub-gr-badge hub-gr-badge-t">TR</span>
            <div>
              <div className="hub-gr-col-name">Plantio da Bomba</div>
              <div className="hub-gr-col-hint">Explodir um dos bombsites</div>
            </div>
          </div>
          <div className="hub-tac-cards">
            {tTactics && Object.entries(tTactics).map(([key, v]) => (
              <TacticOption
                key={key} side="t" tacKey={key} v={v}
                selected={key === selectedT}
                onSelect={() => { onSelectT(key); setPreview({ side: 't', key }); }}
                onHover={() => setPreview({ side: 't', key })}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="hub-gr-footer">
        <div className="hub-gr-footer-label">Sua combinação</div>
        <div className="hub-gr-combo">
          {selectedCT && ctTactics ? (
            <div className="hub-gr-combo-pill hub-gr-combo-pill-ct">
              <span>🛡️</span>{emojiOf(ctTactics[selectedCT])} {cleanLabel(ctTactics[selectedCT].label)}
            </div>
          ) : (
            <div className="hub-gr-combo-empty">— escolha CT</div>
          )}
          {selectedCT && selectedT && <div className="hub-gr-combo-vs">VS</div>}
          {selectedT && tTactics && (
            <div className="hub-gr-combo-pill hub-gr-combo-pill-t">
              <span>💣</span>{emojiOf(tTactics[selectedT])} {cleanLabel(tTactics[selectedT].label)}
            </div>
          )}
        </div>
        <div className="hub-gr-footer-tip">ℹ️&nbsp; {footerTip}</div>
        <Button variant="orange" size="lg" disabled={!canPlay} onClick={onPlay}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3" /></svg>
          {playLabel}
        </Button>
      </div>
    </div>
  );
}

function TacticOption({ side, tacKey, v, selected, onSelect, onHover }) {
  const label = cleanLabel(v.label);
  const emoji = emojiOf(v);
  return (
    <button
      type="button"
      className={`hub-tac-opt ${selected ? (side === 'ct' ? 'sel-ct' : 'sel-t') : ''}`}
      onClick={onSelect}
      onMouseEnter={onHover}
    >
      <div className="hub-tac-inner">
        <div className="hub-tac-opt-label">{emoji} {label}</div>
        <div className="hub-tac-opt-desc">{v.desc || ''}</div>
      </div>
      <div className="hub-tac-thumb">
        <img src={TAC_MAP_IMG[tacKey] || ''} alt={label} loading="lazy" />
      </div>
      <div className="hub-tac-check">✓</div>
    </button>
  );
}

function PreviewContent({ side, tacKey, tactics, oppTactics, matchups }) {
  const v = tactics?.[tacKey];
  if (!v) return null;
  const label = cleanLabel(v.label);
  const emoji = emojiOf(v);
  const oppSide = side === 'ct' ? 't' : 'ct';

  const breakdown = oppTactics ? Object.entries(oppTactics).map(([oppKey, oppV]) => ({
    key: oppKey,
    label: cleanLabel(oppV.label),
    emoji: emojiOf(oppV),
    edge: edgeFor(matchups, side, tacKey, oppKey),
  })) : [];

  return (
    <div>
      <div className="hub-preview-img">
        <img src={TAC_MAP_IMG[tacKey] || ''} alt={label} />
      </div>
      <div className={`hub-preview-badge ${side === 'ct' ? 'hub-preview-badge-ct' : 'hub-preview-badge-t'}`}>
        {side === 'ct' ? 'CT — DEFESA' : 'TR — ATAQUE'}
      </div>
      <div className="hub-preview-name">{emoji} {label}</div>
      <div className="hub-preview-flavor">{v.desc || ''}</div>

      {breakdown.length > 0 && (
        <div className="hub-preview-matchup">
          <div className="hub-pm-title">Contra a resposta {oppSide === 'ct' ? 'CT' : 'TR'} do adversário:</div>
          {breakdown.map((b) => (
            <div className={`hub-pm-row ${b.edge > 0.02 ? 'hub-pm-good' : b.edge < -0.02 ? 'hub-pm-bad' : 'hub-pm-neutral'}`} key={b.key}>
              <span className="hub-pm-opp">{b.emoji} {b.label}</span>
              <span className="hub-pm-bar-track">
                <span className="hub-pm-bar-fill" style={{ width: `${Math.min(100, Math.abs(b.edge) * 700)}%` }} />
              </span>
              <span className="hub-pm-edge">{b.edge > 0 ? '+' : ''}{Math.round(b.edge * 100)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
