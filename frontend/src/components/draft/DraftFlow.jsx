import { useState } from 'react';
import { post } from '../../api/client';
import EraSelect from './EraSelect';
import DraftScreen from './DraftScreen';
import MapPoolScreen from './MapPoolScreen';

// Espelha o fluxo de 3 passos do vanilla (G.draft / _pendingDraftData):
// 1) escolher era → 2) montar elenco (sorteio + slots) → 3) proficiência de
// mapas → POST /api/new_game. Ao terminar, `onGameCreated` avisa o App pra
// buscar o estado novo e trocar pro Hub.
export default function DraftFlow({ onGameCreated }) {
  const [step, setStep] = useState('era'); // 'era' | 'roster' | 'maps'
  const [eraId, setEraId] = useState(null);
  const [rosterData, setRosterData] = useState(null); // { teamName, picks }
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState(null);

  function handleEraConfirm(id) {
    setEraId(id);
    setStep('roster');
  }

  function handleRosterConfirm(data) {
    setRosterData(data);
    setStep('maps');
  }

  async function handleMapsConfirm({ full_maps, half_maps }) {
    setConfirming(true);
    setError(null);
    try {
      const player_picks = rosterData.picks
        .sort((a, b) => a.slotIdx - b.slotIdx)
        .map((pk) => pk.player);

      const r = await post('/api/new_game', {
        team_name: rosterData.teamName,
        player_picks,
        events_enabled: false,
        era_id: eraId,
        full_maps,
        half_maps,
      });

      if (!r.ok) {
        setError(r.error || 'Não foi possível criar a campanha.');
        setConfirming(false);
        return;
      }

      onGameCreated();
    } catch (err) {
      setError(err.message);
      setConfirming(false);
    }
  }

  if (step === 'era') {
    return <EraSelect onConfirm={handleEraConfirm} />;
  }

  if (step === 'roster') {
    return (
      <DraftScreen
        eraId={eraId}
        onBack={() => setStep('era')}
        onConfirm={handleRosterConfirm}
      />
    );
  }

  return (
    <>
      {error && (
        <div style={{
          position: 'fixed', top: 16, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--color-danger)', color: '#fff', padding: '10px 20px',
          borderRadius: 'var(--radius-sm)', zIndex: 100, fontSize: '.85rem',
        }}>
          {error}
        </div>
      )}
      <MapPoolScreen
        onBack={() => setStep('roster')}
        onConfirm={handleMapsConfirm}
        confirming={confirming}
      />
    </>
  );
}
