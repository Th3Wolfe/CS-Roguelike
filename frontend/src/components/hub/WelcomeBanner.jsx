import { useState } from 'react';
import './WelcomeAndHistory.css';

// No vanilla, o CSS (.hub-welcome) e o JS (renderHistoryFeed alternando
// welcome.style.display) já existiam, mas o elemento <div id="hub-welcome">
// nunca foi adicionado ao HTML — então esse banner nunca apareceu de
// verdade. Escrevi o conteúdo do zero aqui, já que não havia nada pra portar.
export default function WelcomeBanner({ teamName }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div className="hub-welcome">
      <div className="hub-welcome-icon">👋</div>
      <div>
        <div className="hub-welcome-title">Bem-vindo, {teamName}!</div>
        <div className="hub-welcome-text">
          Sua campanha está pronta. Clique em <b>Jogar Próxima Série</b> para entrar no veto de mapas
          contra seu primeiro adversário. Acompanhe seu progresso pelo Major nas abas
          <b> Chaveamento</b> e <b>Elenco</b> aqui em cima.
        </div>
      </div>
      <button className="hub-welcome-close" onClick={() => setDismissed(true)}>✕</button>
    </div>
  );
}
