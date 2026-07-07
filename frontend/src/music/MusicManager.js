import { lightningSync } from './lightningSync';

// Port de MusicManager (ver ui/index.html). Continua sendo uma classe JS
// pura — não precisa de React pra funcionar, só é consumida por um Context
// (MusicContext.jsx) pra virar reativa onde a UI precisa (botão de mute,
// slider de volume).
const ONE_SHOT_TRACKS = {
  victory: '/ui/music/victory.mp3',
  defeat: '/ui/music/defeat.mp3',
};

export class MusicManager {
  constructor() {
    this.playlists = { frontend: [], hub: [], match: [] };
    this.remainingTracks = { frontend: [], hub: [], match: [] };
    this.currentContext = null;
    this.currentTrack = null;

    this.audio = new Audio();
    this.audio.addEventListener('ended', () => this._onEnded());

    this.volume = 0.4;
    this._muted = false;
    this.audio.volume = this.volume;

    this._oneShotActive = false;
    this._returnContext = null;
    this._fadeId = null;
    this._pendingContext = null;
    this._pendingOneShot = null;

    this._unlock = () => this._tryUnlock();
    ['click', 'keydown', 'touchstart', 'pointerdown'].forEach((ev) =>
      document.addEventListener(ev, this._unlock)
    );
  }

  _refill(ctx) {
    const fresh = [...(this.playlists[ctx] || [])];
    for (let i = fresh.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [fresh[i], fresh[j]] = [fresh[j], fresh[i]];
    }
    this.remainingTracks[ctx] = fresh;
  }

  _nextTrack(ctx) {
    if (!this.remainingTracks[ctx] || this.remainingTracks[ctx].length === 0) this._refill(ctx);
    return this.remainingTracks[ctx].pop();
  }

  setContext(ctx) {
    if (!this.playlists[ctx]) return;
    if (this.currentContext === ctx && !this._oneShotActive) return;
    this.currentContext = ctx;
    this._oneShotActive = false;
    this._playFromContext(ctx);
  }

  _playFromContext(ctx) {
    const track = this._nextTrack(ctx);
    if (!track) return;
    this._crossfadeTo(track);
  }

  playNext() {
    if (!this.currentContext) return;
    this._playFromContext(this.currentContext);
  }

  _onEnded() {
    if (this._oneShotActive) {
      this._oneShotActive = false;
      if (this._returnContext) this.setContext(this._returnContext);
      return;
    }
    this.playNext();
  }

  playOnce(name) {
    const src = ONE_SHOT_TRACKS[name];
    if (!src) return;
    this._oneShotActive = true;
    this._returnContext = this.currentContext;
    this._crossfadeTo(src);
  }

  _crossfadeTo(src) {
    const FADE_MS = 800;
    const startNewTrack = () => {
      this.audio.pause();
      this.currentTrack = src;
      this.audio.src = src;
      this.audio.currentTime = 0;
      this.audio.volume = 0;

      if (this.currentContext === 'frontend') lightningSync.connect(this.audio);
      else lightningSync.disconnect();

      const playPromise = this.audio.play();
      if (playPromise && playPromise.then) {
        playPromise
          .then(() => this._fadeTo(this._muted ? 0 : this.volume, FADE_MS))
          .catch(() => {
            if (this._oneShotActive) this._pendingOneShot = src;
            else this._pendingContext = this.currentContext;
          });
      }
    };

    if (this.currentTrack && !this.audio.paused) {
      this._fadeTo(0, FADE_MS, startNewTrack);
    } else {
      startNewTrack();
    }
  }

  _fadeTo(target, ms, onDone) {
    if (this._fadeId) clearInterval(this._fadeId);
    const step = 50;
    const steps = Math.max(1, ms / step);
    const delta = (target - this.audio.volume) / steps;
    let n = 0;
    this._fadeId = setInterval(() => {
      n++;
      this.audio.volume = Math.max(0, Math.min(1, this.audio.volume + delta));
      if (n >= steps) {
        clearInterval(this._fadeId);
        this.audio.volume = target;
        if (onDone) onDone();
      }
    }, step);
  }

  _tryUnlock() {
    if (this._pendingOneShot) {
      const src = this._pendingOneShot;
      this._pendingOneShot = null;
      this._oneShotActive = true;
      this._crossfadeTo(src);
    } else if (this._pendingContext) {
      const ctx = this._pendingContext;
      this._pendingContext = null;
      this.currentContext = null;
      this.setContext(ctx);
    }
  }

  stop() {
    this._fadeTo(0, 400, () => { this.audio.pause(); this.audio.currentTime = 0; });
    this.currentContext = null;
    this._oneShotActive = false;
  }

  setVolume(v) {
    this.volume = Math.max(0, Math.min(1, v));
    if (!this._muted) this.audio.volume = this.volume;
  }

  toggleMute() {
    this._muted = !this._muted;
    this.audio.volume = this._muted ? 0 : this.volume;
    return this._muted;
  }

  setPlaylists(tracks) {
    Object.keys(tracks).forEach((ctx) => {
      this.playlists[ctx] = tracks[ctx] || [];
      this.remainingTracks[ctx] = [];
    });
    if (this.currentContext && !this.currentTrack && !this._oneShotActive) {
      this._playFromContext(this.currentContext);
    }
  }

  destroy() {
    ['click', 'keydown', 'touchstart', 'pointerdown'].forEach((ev) =>
      document.removeEventListener(ev, this._unlock)
    );
    this.audio.pause();
  }
}
