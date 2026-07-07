import { useRef, useState } from 'react';
import { useMusic } from '../../music/MusicContext';
import './MusicButton.css';

export default function MusicButton() {
  const { muted, toggleMute, volume, setVolume } = useMusic();
  const [popupVisible, setPopupVisible] = useState(false);
  const hideTimer = useRef(null);

  function showPopup() {
    if (hideTimer.current) clearTimeout(hideTimer.current);
    setPopupVisible(true);
  }
  function scheduleHide() {
    hideTimer.current = setTimeout(() => setPopupVisible(false), 400);
  }

  return (
    <>
      <button
        className={`music-btn ${muted ? 'muted' : ''}`}
        title="Música"
        onClick={toggleMute}
        onMouseEnter={showPopup}
        onMouseLeave={scheduleHide}
      >
        {muted ? '🔇' : '🎵'}
      </button>
      <div className={`music-popup ${popupVisible ? 'visible' : ''}`} onMouseEnter={showPopup} onMouseLeave={scheduleHide}>
        <div className="vol-label"><span>Volume</span><span className="vol-value">{Math.round(volume * 100)}%</span></div>
        <input
          type="range" min="0" max="1" step="0.05" value={volume}
          onChange={(e) => setVolume(parseFloat(e.target.value))}
        />
      </div>
    </>
  );
}
