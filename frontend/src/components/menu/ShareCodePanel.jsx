import { useState } from 'react';
import { post } from '../../api/client';
import Button from '../ui/Button';

// share_decode retorna campos abreviados (economizar espaço no código):
// n=nome do time, s=sinergia, p=jogadores [{k=nick, e=era, r=role, rtg}]
export default function ShareCodePanel({ onClose }) {
  const [code, setCode] = useState('');
  const [teamData, setTeamData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleDecode() {
    const trimmed = code.trim();
    if (!trimmed) { setError('Cole um código primeiro'); return; }
    setLoading(true);
    setError(null);
    try {
      const r = await post('/api/share_decode', { code: trimmed });
      if (!r.ok) { setError('Código inválido'); setTeamData(null); return; }
      setTeamData(r.team_data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="share-overlay" onClick={onClose}>
      <div className="share-modal" onClick={(e) => e.stopPropagation()}>
        <div className="share-modal-title">
          <span>Ver Time por Código</span>
          <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
        </div>

        <input
          className="share-code-input"
          placeholder="Cole o código do time aqui…"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleDecode()}
        />
        <Button variant="orange" onClick={handleDecode} disabled={loading} style={{ width: '100%', justifyContent: 'center', marginBottom: 12 }}>
          {loading ? 'Decodificando…' : 'Ver Time'}
        </Button>

        {error && <div style={{ color: 'var(--color-danger)', fontSize: '.82rem', marginBottom: 8 }}>{error}</div>}

        {teamData && (
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '.9rem', fontWeight: 700, color: 'var(--orange)', marginBottom: 8 }}>
              {teamData.n}
            </div>
            <div style={{ fontSize: '.75rem', color: 'var(--text2)', marginBottom: 6 }}>
              Sinergia: {teamData.s > 0 ? '+' : ''}{teamData.s}
            </div>
            {(teamData.p || []).map((p, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0',
                borderBottom: '1px solid var(--border)', fontSize: '.8rem',
              }}>
                <span style={{ fontWeight: 700, color: 'var(--orange)' }}>{p.k}</span>
                <span style={{ color: 'var(--text3)' }}>{p.e || '?'}</span>
                <span style={{ color: 'var(--text2)' }}>{p.r}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--blue)' }}>RTG {p.rtg}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
