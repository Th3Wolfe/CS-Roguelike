import { useEffect, useState } from 'react';
import './IntroScreen.css';

// Port de #screen-intro. Existe porque navegadores bloqueiam autoplay de
// áudio sem uma interação explícita do usuário — esse clique é o gesto que
// desbloqueia o MusicManager (ver document.addEventListener em
// MusicManager.js, que já escuta 'click' globalmente).
export default function IntroScreen({ onEnter }) {
  const [ready, setReady] = useState(false);
  const [fadingOut, setFadingOut] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setReady(true), 50);
    return () => clearTimeout(t);
  }, []);

  function handleClick() {
    if (fadingOut) return;
    setFadingOut(true);
    onEnter();
  }

  return (
    <div className={`intro-screen ${ready ? 'ready' : ''} ${fadingOut ? 'fade-out' : ''}`} onClick={handleClick}>
      <div className="intro-title">CS Major<br /><span>Manager</span></div>
      <div className="intro-rule" />
      <div className="intro-sub">Counter-Strike · Season 2026</div>
      <div className="intro-cta">Clique para entrar</div>
    </div>
  );
}
