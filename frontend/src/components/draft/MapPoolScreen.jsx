import { useEffect, useState } from 'react';
import { get } from '../../api/client';
import Button from '../ui/Button';
import '../ui/screenChrome.css';
import './MapPoolScreen.css';

export default function MapPoolScreen({ onBack, onConfirm, confirming }) {
  const [maps, setMaps] = useState([]);
  const [ctBias, setCtBias] = useState({});
  const [full, setFull] = useState([]);
  const [half, setHalf] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    get('/api/map_pool')
      .then((r) => { setMaps(r.maps); setCtBias(r.ct_bias || {}); })
      .catch((err) => setError(err.message));
  }, []);

  function toggleMap(m) {
    if (full.includes(m)) {
      setFull((prev) => prev.filter((x) => x !== m));
    } else if (half.includes(m)) {
      setHalf((prev) => prev.filter((x) => x !== m));
    } else if (full.length < 2) {
      setFull((prev) => [...prev, m]);
    } else if (half.length < 3) {
      setHalf((prev) => [...prev, m]);
    }
  }

  const canConfirm = full.length === 2 && half.length === 3;

  return (
    <div className="maps-screen">
      <div className="screen-topbar">
        <div className="screen-topbar-left">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
            Time
          </Button>
          <span className="screen-topbar-title">Proficiência de Mapas</span>
        </div>
        <div className="screen-topbar-spacer" />
        <span className="screen-topbar-meta">Passo 3 de 3</span>
        <span className="screen-topbar-meta" style={{ marginLeft: 16, color: 'var(--text2)' }}>
          {full.length}/2 Full · {half.length}/3 Half
        </span>
      </div>

      <div className="setup-scroll">
        <div style={{ marginBottom: 24 }}>
          <div className="section-head" style={{ fontSize: '.9rem', letterSpacing: '.12em', marginBottom: 10 }}>
            Como seu time joga cada mapa?
          </div>
          <div style={{ fontSize: '.88rem', color: 'var(--text2)', lineHeight: 1.7, maxWidth: 680 }}>
            Isso define o <b style={{ color: 'var(--color-text-primary)' }}>bônus ou penalidade de desempenho</b> quando
            você jogar nesses mapas. Clique nos mapas para alternar a proficiência — os dois últimos sem clique ficarão
            em <b style={{ color: 'var(--color-danger)' }}>Nula</b>.
          </div>
        </div>

        <div className="mp-legend" style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
          <div className="mp-leg-item"><div className="mp-leg-dot" style={{ background: 'var(--green)' }} /><span>Full (+6% win rate)</span></div>
          <div className="mp-leg-item"><div className="mp-leg-dot" style={{ background: 'var(--orange)' }} /><span>Half (neutro)</span></div>
          <div className="mp-leg-item"><div className="mp-leg-dot" style={{ background: 'var(--red)' }} /><span>Nula (−10% win rate)</span></div>
        </div>

        {error && <div style={{ color: 'var(--color-danger)' }}>Erro: {error}</div>}

        <div className="mp-grid">
          {maps.map((m) => {
            const isFull = full.includes(m);
            const isHalf = half.includes(m);
            const isNone = !isFull && !isHalf && full.length >= 2 && half.length >= 3;
            const cls = isFull ? 'mp-full' : isHalf ? 'mp-half' : isNone ? 'mp-none' : '';
            const tier = isFull ? '✓ Full' : isHalf ? '◑ Half' : isNone ? '✗ Nula' : 'Clique para selecionar';
            const bias = ctBias[m];
            const biasLbl = bias ? (bias > 0.52 ? 'CT-sided' : bias < 0.48 ? 'T-sided' : 'Balanced') : '';
            return (
              <div key={m} className={`mp-card ${cls}`} onClick={() => toggleMap(m)}>
                <div className="mp-card-name">{m}</div>
                <div className="mp-card-bias">{biasLbl}</div>
                <span className="mp-card-tier">{tier}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="setup-action-bar" style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="orange" size="lg" disabled={!canConfirm || confirming} onClick={() => onConfirm({ full_maps: full, half_maps: half })}>
          {confirming ? 'Criando campanha…' : 'Confirmar e Iniciar Major →'}
        </Button>
      </div>
    </div>
  );
}
