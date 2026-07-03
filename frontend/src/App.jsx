import { useGameState } from './hooks/useGameState';
import HubInfoStrip from './components/hub/HubInfoStrip';
import DraftFlow from './components/draft/DraftFlow';

// Fatias migradas até aqui:
//  - Draft completo (Era → Elenco → Mapas), que termina criando a campanha
//  - Faixa de 3 cards do topo do Hub (Campanha Atual / Último Resultado / Próxima Partida)
// O resto (veto, partida, roster, chaveamento completo...) ainda vive em
// ui/index.html e continua sendo migrado incrementalmente aqui dentro.
export default function App() {
  const { state, loading, error, refresh } = useGameState();

  if (loading) {
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

  if (!state) {
    // Sem campanha na sessão: joga o fluxo de criação de time.
    // Ao terminar (new_game concluído), refresh() busca o estado novo e
    // esse mesmo App já troca sozinho pro Hub abaixo.
    return <DraftFlow onGameCreated={refresh} />;
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px' }}>
      <HubInfoStrip
        team={state.team}
        campaign={state.campaign}
        bracket={state.bracket}
      />
    </div>
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
