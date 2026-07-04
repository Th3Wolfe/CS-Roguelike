import { useEffect, useState } from 'react';
import { useGameState } from './hooks/useGameState';
import DraftFlow from './components/draft/DraftFlow';
import VetoScreen from './components/veto/VetoScreen';
import MainMenu from './components/menu/MainMenu';
import HubScreen from './components/hub/HubScreen';

// Fatias migradas até aqui:
//  - Menu principal (Novo Jogo / Carregar Save / Ver Time por Código)
//  - Draft completo (Era → Elenco → Mapas), que termina criando a campanha
//  - Hub completo (topbar, abas Hub/Chaveamento/Elenco, histórico, bracket)
//  - Veto de mapas (Pick & Ban) + disparo da simulação da série
// Ainda faltam: tela de táticas (por enquanto play_series roda sem táticas
// customizadas) e tela de partida com animação de placar. Esses continuam
// em ui/index.html e são migrados incrementalmente aqui.
export default function App() {
  const { state, loading, error, refresh } = useGameState();
  // 'menu' | 'draft' | 'hub' | 'veto' — navegação de tela única.
  const [screen, setScreen] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [tactics, setTactics] = useState({ ct: null, t: null });

  // Assim que sabemos se há campanha ou não (primeiro load), define a tela
  // inicial. Depois disso a navegação é toda via cliques do usuário.
  useEffect(() => {
    if (screen === null && !loading) {
      setScreen(state ? 'hub' : 'menu');
    }
  }, [loading, state, screen]);

  if (loading || screen === null) {
    return <Centered>Carregando...</Centered>;
  }

  if (error) {
    return (
      <Centered>
        Não foi possível falar com o servidor.{' '}
        <button onClick={refresh}>Tentar de novo</button>
      </Centered>
    );
  }

  if (screen === 'menu') {
    return (
      <MainMenu
        onNewGame={() => setScreen('draft')}
        onGameLoaded={async () => { await refresh(); setScreen('hub'); }}
      />
    );
  }

  if (screen === 'draft') {
    return (
      <DraftFlow
        onGameCreated={async () => { await refresh(); setScreen('hub'); }}
        onBack={() => setScreen('menu')}
      />
    );
  }

  if (screen === 'veto') {
    return (
      <VetoScreen
        team={state.team}
        tactics={tactics}
        onBack={() => setScreen('hub')}
        onComplete={async (r) => {
          await refresh();
          setLastResult(r.result);
          setTactics({ ct: null, t: null });
          setScreen('hub');
        }}
      />
    );
  }

  // screen === 'hub'
  if (!state) {
    // Estado inconsistente (ex: sessão expirou) — volta pro menu.
    setScreen('menu');
    return null;
  }

  return (
    <HubScreen
      state={state}
      lastResult={lastResult}
      tactics={tactics}
      onSelectCT={(ct) => setTactics((t) => ({ ...t, ct }))}
      onSelectT={(t2) => setTactics((t) => ({ ...t, t: t2 }))}
      onPlaySeries={() => { setLastResult(null); setScreen('veto'); }}
      onBackToMenu={() => setScreen('menu')}
    />
  );
}

function Centered({ children }) {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', color: 'var(--text2)', fontFamily: 'var(--font-body)',
    }}>
      {children}
    </div>
  );
}
