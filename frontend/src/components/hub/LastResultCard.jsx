import './hub.css';

// `lastWinProbability` é opcional: só existe logo após jogar uma série
// (vem de result.win_probability na resposta de /api/play_series), não faz
// parte do /api/state. Enquanto essa tela ainda não estiver migrada, passe
// null — o card funciona normalmente, só sem a nota de "% de chance".
export default function LastResultCard({ campaign, lastWinProbability = null }) {
  const history = campaign?.history || [];
  const last = history[history.length - 1];

  if (!last) {
    return (
      <div className="hub-info-card">
        <div className="hub-ic-label">Último Resultado</div>
        <div className="hub-ic-result-label">–</div>
      </div>
    );
  }

  const won = last.result === 'win';

  return (
    <div className="hub-info-card">
      <div className="hub-ic-label">Último Resultado</div>
      <div className={`hub-ic-result-label ${won ? 'win' : 'loss'}`}>
        {won ? 'VITÓRIA' : 'DERROTA'}
      </div>
      <div className="hub-ic-result-vs">vs {last.opponent_name}</div>
      {lastWinProbability != null && (
        <div className="hub-ic-result-note">
          Eram {Math.round(lastWinProbability * 100)}% de chance
        </div>
      )}
    </div>
  );
}
