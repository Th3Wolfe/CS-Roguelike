import { useEffect, useState } from 'react';
import { get } from '../../api/client';
import Button from '../ui/Button';
import './EraSelect.css';

const CHECK_ICON = (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#000"
    strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

export default function EraSelect({ onConfirm, onBack }) {
  const [eras, setEras] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    get('/api/eras')
      .then((r) => setEras(r.eras))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="era-screen">
      {onBack && (
        <div style={{ position: 'absolute', top: 16, left: 20, zIndex: 2 }}>
          <Button variant="ghost" size="sm" onClick={onBack}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
            Voltar
          </Button>
        </div>
      )}
      <div className="era-inner">
        <div className="era-eyebrow">CS Major Manager</div>
        <div className="era-title">Escolha a <span>Era</span></div>
        <div className="era-sub">
          Cada era tem seu próprio elenco de times e jogadores reais — isso
          define quem você pode montar e quem vai enfrentar na campanha.
        </div>

        {error && <div style={{ color: 'var(--color-danger)', marginBottom: 16 }}>{error}</div>}
        {!eras && !error && <div style={{ color: 'var(--text2)' }}>Carregando eras…</div>}

        <div className="era-grid">
          {(eras || []).map((e) => {
            const isSelected = selected === e.id;
            const [, labelRest] = e.label.split('—');
            return (
              <div
                key={e.id}
                className={`era-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setSelected(e.id)}
              >
                <div className="era-year">{e.id}</div>
                <div className="era-info">
                  <div className="era-label">{(labelRest || e.label).trim()}</div>
                  <div className="era-desc">{e.description}</div>
                </div>
                <div className="era-check">{isSelected && CHECK_ICON}</div>
              </div>
            );
          })}
        </div>

        <Button variant="orange" size="lg" disabled={!selected} onClick={() => onConfirm(selected)}>
          Continuar
        </Button>
      </div>
    </div>
  );
}
