import { useEffect, useState } from 'react';
import { get, post } from '../../api/client';

// O botão "Carregar Save" no vanilla chamava onclick="openLoads()" — mas
// essa função nunca foi definida em lugar nenhum do index.html. O botão
// não fazia nada (erro silencioso no console). Implementado aqui de verdade,
// usando os endpoints que já existem no Flask (/api/saves e /api/load).
function parseSaveFilename(filename) {
  // Formato: save_<TeamName>_<YYYYMMDD>_<HHMMSS>.json
  const m = filename.match(/^save_(.+)_(\d{8})_(\d{6})\.json$/);
  if (!m) return { name: filename, date: '' };
  const [, name, ymd, hms] = m;
  const date = `${ymd.slice(6, 8)}/${ymd.slice(4, 6)}/${ymd.slice(0, 4)} ${hms.slice(0, 2)}:${hms.slice(2, 4)}`;
  return { name, date };
}

export default function LoadSavePanel({ onLoaded }) {
  const [saves, setSaves] = useState(null);
  const [error, setError] = useState(null);
  const [loadingFile, setLoadingFile] = useState(null);

  useEffect(() => {
    get('/api/saves')
      .then((r) => setSaves(r.saves || []))
      .catch((err) => setError(err.message));
  }, []);

  async function handleLoad(filename) {
    setLoadingFile(filename);
    setError(null);
    try {
      const r = await post('/api/load', { filename });
      if (!r.ok) { setError(r.error || 'Erro ao carregar save'); setLoadingFile(null); return; }
      onLoaded();
    } catch (err) {
      setError(err.message);
      setLoadingFile(null);
    }
  }

  return (
    <div id="load-saves-panel" className="menu-panel">
      {error && <div style={{ color: 'var(--color-danger)', fontSize: '.8rem', padding: '6px 8px' }}>{error}</div>}
      {saves === null && !error && <div className="menu-panel-empty">Carregando saves…</div>}
      {saves?.length === 0 && <div className="menu-panel-empty">Nenhum save encontrado.</div>}
      {saves?.map((filename) => {
        const { name, date } = parseSaveFilename(filename);
        return (
          <div className="save-item" key={filename} onClick={() => handleLoad(filename)}>
            <span className="save-item-name">{name}</span>
            <span className="save-item-date">{loadingFile === filename ? 'Carregando…' : date}</span>
          </div>
        );
      })}
    </div>
  );
}
