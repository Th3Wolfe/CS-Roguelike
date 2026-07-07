import { useEffect, useRef } from 'react';
import { lightningSync } from '../../music/lightningSync';

// Componente fino: só registra os elementos DOM que lightningSync.js precisa
// (o <svg> onde os raios são desenhados, e o container onde as partículas de
// impacto são posicionadas) e chama start()/stop() no ciclo de vida do
// componente. Toda a lógica de animação fica no módulo (é imperativa por
// natureza — recriar isso "à la React" só pioraria a performance).
export default function LightningCanvas({ containerRef }) {
  const svgRef = useRef(null);

  useEffect(() => {
    lightningSync.setCanvas(svgRef.current);
    lightningSync.setContainer(containerRef.current);
    lightningSync.start();
    return () => lightningSync.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <svg
      ref={svgRef}
      id="lightning-canvas"
      viewBox="0 0 600 700"
      preserveAspectRatio="xMidYMid meet"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 2 }}
    />
  );
}
