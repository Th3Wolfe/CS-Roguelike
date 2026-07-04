import { useMemo } from 'react';

// Mesma lógica do initMenuParticles() vanilla: 80 partículas com posição,
// tamanho, delay e duração aleatórios, geradas uma vez e animadas via CSS
// (@keyframes particleFloat, infinito) — não precisa de re-render em loop.
const PARTICLE_COUNT = 80;

export default function MenuParticles() {
  const particles = useMemo(() => (
    Array.from({ length: PARTICLE_COUNT }, () => {
      const size = 1 + Math.random() * 3;
      return {
        left: `${Math.random() * 100}%`,
        bottom: `${Math.random() * 35}%`,
        width: `${size}px`,
        height: `${size}px`,
        animationDelay: `${Math.random()}s`,
        animationDuration: `${3 + Math.random() * 3}s`,
      };
    })
  ), []);

  return (
    <div className="menu-particles">
      {particles.map((style, i) => (
        <div key={i} className="menu-particle" style={style} />
      ))}
    </div>
  );
}
