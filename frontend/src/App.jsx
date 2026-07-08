import { useEffect, useState } from 'react';
import { useGameState } from './hooks/useGameState';
import { useMusic } from './music/MusicContext';
import DraftFlow from './components/draft/DraftFlow';
import VetoScreen from './components/veto/VetoScreen';
import MatchScreen from './components/match/MatchScreen';
import StageModal from './components/match/StageModal';
import MainMenu from './components/menu/MainMenu';
import HubScreen from './components/hub/HubScreen';
import IntroScreen from './components/intro/IntroScreen';
import MusicButton from './components/music/MusicButton';

// Fatias migradas até aqui:
//  - Tela de intro (desbloqueia áudio) + música ambiente por cena + raio no menu
//  - Menu principal (Novo Jogo / Carregar Save / Ver Time por Código)
//  - Draft completo (Era → Elenco → Mapas, com drag & drop), que termina
//    criando a campanha
//  - Hub completo (topbar, abas Hub/Chaveamento/Elenco, histórico, bracket
//    fiel round-a-round, painel de táticas)
//  - Veto de mapas (Pick & Ban)
//  - Partida resolvida mapa a mapa, com Pause Técnico de uso único por
//    partida — disponível o tempo todo durante a animação (inclusive no
//    meio de um mapa: a animação pausa de verdade), mas só afeta os mapas
//    que ainda não foram pedidos ao backend
//  - Modal de transição de estágio (avançou/eliminado/campeão) + música de
//    vitória/derrota (só toca no fim da campanha, igual ao vanilla)
// Fora de escopo por enquanto: pause simulado do adversário.
const SCREEN_MUSIC = {
  menu: 'frontend',
  draft: 'frontend',
  hub: 'hub',
  veto: 'match',
  match: 'hub',
};

export default function App() {
  const { state, loading, error, refresh } = useGameState();
  const { setContext, playOnce } = useMusic();
  const [introDone, setIntroDone] = useState(false);
  // 'menu' | 'draft' | 'hub' | 'veto' | 'match' — navegação de tela única.
  const [screen, setScreen] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [tactics, setTactics] = useState({ ct: null, t: null });
  const [matchOpponentName, setMatchOpponentName] = useState('');
  // Modal de transição de estágio (avançou/eliminado/campeão), mostrado por
  // cima da Hub logo que a partida termina, se a fase da campanha mudou.
  const [stageModal, setStageModal] = useState(null); // { kind, newStage, stageMvp, history }

  // Assim que sabemos se há campanha ou não (primeiro load), define a tela
  // inicial. Depois disso a navegação é toda via cliques do usuário.
  useEffect(() => {
    if (screen === null && !loading) {
      setScreen(state ? 'hub' : 'menu');
    }
  }, [loading, state, screen]);

  useEffect(() => {
    if (introDone && screen) setContext(SCREEN_MUSIC[screen] || 'frontend');
  }, [introDone, screen, setContext]);

  if (!introDone) {
    return <IntroScreen onEnter={() => setIntroDone(true)} />;
  }

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

  return (
    <>
      {renderScreen()}
      <MusicButton />
    </>
  );

  function renderScreen() {
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
          onBack={() => setScreen('hub')}
          onSeriesPlayed={(oppName) => { setMatchOpponentName(oppName); setScreen('match'); }}
        />
      );
    }

    if (screen === 'match') {
      return (
        <MatchScreen
          team={state.team}
          opponentName={matchOpponentName}
          initialTactics={tactics}
          onDone={async (finishResult) => {
            const prevStage = state.campaign.stage;
            const newStage = finishResult.campaign.stage;

            await refresh();
            setLastResult(finishResult.result);
            setTactics({ ct: null, t: null });
            setMatchOpponentName('');
            setScreen('hub');

            // Igual ao vanilla (closeMatch → showStageModal): só mostra o
            // modal se a fase realmente mudou entre o início e o fim dessa
            // partida. A música de vitória/derrota (one-shot) também só
            // toca aqui, no fim da CAMPANHA — não depois de cada partida.
            if (newStage === 'finished_win' || newStage === 'finished_loss') {
              playOnce(newStage === 'finished_win' ? 'victory' : 'defeat');
              setStageModal({
                kind: newStage === 'finished_win' ? 'champ' : 'elim',
                newStage,
                stageMvp: finishResult.result.stage_mvp,
                history: finishResult.campaign.history,
              });
            } else if (newStage !== prevStage) {
              setStageModal({
                kind: 'advance',
                newStage,
                stageMvp: finishResult.result.stage_mvp,
                history: finishResult.campaign.history,
              });
            }
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
      <>
        <HubScreen
          state={state}
          lastResult={lastResult}
          tactics={tactics}
          onSelectCT={(ct) => setTactics((t) => ({ ...t, ct }))}
          onSelectT={(t2) => setTactics((t) => ({ ...t, t: t2 }))}
          onPlaySeries={() => { setLastResult(null); setScreen('veto'); }}
          onBackToMenu={() => setScreen('menu')}
        />
        {stageModal && (
          <StageModal
            kind={stageModal.kind}
            team={state.team}
            history={stageModal.history}
            newStage={stageModal.newStage}
            stageMvp={stageModal.stageMvp}
            onContinue={() => setStageModal(null)}
          />
        )}
      </>
    );
  }
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
