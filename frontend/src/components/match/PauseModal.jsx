import TacticsPanel from '../hub/TacticsPanel';

// Reaproveita o mesmo TacticsPanel da Hub (mesmas cards, mesmo preview),
// só que dentro de um modal sobre a animação da partida, com textos e rótulo
// de botão diferentes. `selectedCT`/`selectedT` chegam com o valor ATUAL
// (podem já ter sido trocados numa pausa anterior — mas só existe uma por
// partida, então na prática sempre é a escolha original da Hub).
export default function PauseModal({ selectedCT, selectedT, onSelectCT, onSelectT, onConfirm, mapsRemaining }) {
  return (
    <div className="pause-overlay">
      <div className="pause-modal">
        <div className="pause-modal-banner">⏸ Pause Técnico — uso único nesta partida</div>
        <TacticsPanel
          selectedCT={selectedCT}
          selectedT={selectedT}
          onSelectCT={onSelectCT}
          onSelectT={onSelectT}
          onPlay={onConfirm}
          eyebrow="Pause técnico"
          title="🧠 Reveja seu plano de jogo"
          subtitle={`Você pode manter ou trocar a tática de CT e de TR agora. Isso vale para ${mapsRemaining > 1 ? `os ${mapsRemaining} mapas restantes` : 'o mapa restante'} — os mapas já jogados não mudam.`}
          footerTip={<>Esse é o seu <b>único pause</b> nesta partida — depois de confirmar, não dá mais para editar.</>}
          playLabel="Confirmar e Continuar"
        />
      </div>
    </div>
  );
}
