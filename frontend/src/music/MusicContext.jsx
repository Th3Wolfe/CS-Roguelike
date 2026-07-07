import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { MusicManager } from './MusicManager';
import { get } from '../api/client';

const MusicCtx = createContext(null);

export function MusicProvider({ children }) {
  const managerRef = useRef(null);
  if (!managerRef.current) managerRef.current = new MusicManager();
  const manager = managerRef.current;

  const [muted, setMuted] = useState(false);
  const [volume, setVolumeState] = useState(manager.volume);

  useEffect(() => {
    get('/api/music_tracks')
      .then((r) => { if (r.ok && r.tracks) manager.setPlaylists(r.tracks); })
      .catch(() => { /* backend indisponível — segue sem música até conseguir carregar */ });
    // Sem cleanup/destroy aqui de propósito: o MusicProvider envolve o app
    // inteiro pela vida toda da página, nunca desmonta de verdade — e em
    // StrictMode (dev) o efeito roda 2x (mount→unmount→mount); se
    // destruíssemos o manager no meio disso, os listeners de desbloqueio de
    // áudio (click/keydown/touchstart) seriam removidos e nunca
    // recolocados, quebrando o áudio só em dev.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const api = {
    setContext: (ctx) => manager.setContext(ctx),
    playOnce: (name) => manager.playOnce(name),
    muted,
    toggleMute: () => setMuted(manager.toggleMute()),
    volume,
    setVolume: (v) => { manager.setVolume(v); setVolumeState(v); },
  };

  return <MusicCtx.Provider value={api}>{children}</MusicCtx.Provider>;
}

export function useMusic() {
  const ctx = useContext(MusicCtx);
  if (!ctx) {
    // Fora do Provider (ex: em testes) — no-op seguro, nunca quebra a tela.
    return { setContext: () => {}, playOnce: () => {}, muted: false, toggleMute: () => {}, volume: 0.4, setVolume: () => {} };
  }
  return ctx;
}
