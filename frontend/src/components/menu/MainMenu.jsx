import { useState } from 'react';
import Button from '../ui/Button';
import MenuParticles from './MenuParticles';
import LoadSavePanel from './LoadSavePanel';
import ShareCodePanel from './ShareCodePanel';
import './MainMenu.css';

// Tela de entrada do jogo. Substitui #screen-menu do vanilla.
// Simplificação consciente: o vanilla tinha um sistema de raio (canvas SVG
// sincronizado com a música, window.LightningSync) sobre a arte hexagonal —
// não portado aqui ainda. As partículas flutuantes (MenuParticles) e o pulso
// de glow no hexágono (CSS puro) foram mantidos.
export default function MainMenu({ onNewGame, onGameLoaded }) {
  const [showLoads, setShowLoads] = useState(false);
  const [showShare, setShowShare] = useState(false);

  return (
    <div className="menu-screen">
      <MenuParticles />

      <div className="menu-inner">
        <div className="menu-left">
          <div className="menu-brand">
            <div className="menu-brand-eyebrow">Roguelike · Strategy</div>
            <h1 className="menu-brand-title">CS Major<br /><span>Manager</span></h1>
            <div className="menu-brand-sub">Counter-Strike · Season 2026</div>
            <div className="menu-brand-version">v4.0 — Build Stable</div>
          </div>

          <div className="menu-btns">
            <Button variant="orange" onClick={onNewGame}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3" /></svg>
              Novo Jogo
            </Button>
            <hr className="menu-divider" />
            <Button variant="ghost" onClick={() => setShowLoads((v) => !v)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>
              Carregar Save
            </Button>
            <Button variant="ghost" onClick={() => setShowShare(true)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" /></svg>
              Ver Time por Código
            </Button>
          </div>

          {showLoads && <LoadSavePanel onLoaded={onGameLoaded} />}

          <div className="menu-howto">
            <div className="menu-howto-title">Como jogar</div>
            <div className="menu-howto-steps">
              <div className="menu-howto-step">
                <span className="mhs-num">1</span>
                <span>Escolha uma <b>Era</b> e monte seu <b>time de 5 jogadores</b> no Draft</span>
              </div>
              <div className="menu-howto-step">
                <span className="mhs-num">2</span>
                <span>Defina suas <b>táticas</b> (CT e TR) e <b>jogue as partidas</b> do Major</span>
              </div>
              <div className="menu-howto-step">
                <span className="mhs-num">3</span>
                <span>Vença séries, avance nas fases e <b>conquiste o Major</b> 🏆</span>
              </div>
            </div>
          </div>
        </div>

        <div className="menu-right">
          <div className="menu-hex-art">
            <img src="/ui/static/CS_Manager_Logo_2.png" alt="Major Manager" />
          </div>
        </div>
      </div>

      <div className="menu-footer">CS Major Manager &nbsp;·&nbsp; Iago Martins &nbsp;·&nbsp; 2026</div>

      {showShare && <ShareCodePanel onClose={() => setShowShare(false)} />}
    </div>
  );
}
