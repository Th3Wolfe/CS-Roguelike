import { useState } from 'react';
import { shieldUrl } from '../../utils/teamShield';
import './hub.css';

// Círculo de escudo. Se `/ui/static/shields/<slug>.png` não existir (ainda
// não desenhado pra esse time), cai pro emoji de fallback sem quebrar o
// layout — mesmo comportamento da versão vanilla.
export default function TeamShield({ teamName, fallback }) {
  const [broken, setBroken] = useState(false);

  if (!teamName || broken) {
    return <div className="hub-ic-shield">{fallback}</div>;
  }

  return (
    <div className="hub-ic-shield">
      <img src={shieldUrl(teamName)} alt={teamName} onError={() => setBroken(true)} />
    </div>
  );
}
