export const STAGE_LABELS = {
  stage1: 'Stage 1',
  stage2: 'Stage 2',
  playoffs_qf: 'Quartas de Final',
  playoffs_sf: 'Semifinal',
  playoffs_final: 'Grande Final',
  finished_win: '🏆 Campeão',
  finished_loss: '❌ Eliminado',
};

// Usado no card "Campanha Atual" (subtítulo curto).
export const STAGE_FORMATS = {
  stage1: 'Formato Swiss — 3V avança, 3D = eliminado.',
  stage2: 'Swiss novamente. Adversários mais difíceis.',
  playoffs_qf: 'Quartas de Final — eliminação direta.',
  playoffs_sf: 'Semifinal — sem segunda chance.',
  playoffs_final: 'Grande Final — tudo ou nada.',
  finished_win: '🏆 Você conquistou o Major!',
  finished_loss: '❌ Eliminado.',
};

export function isStageFinished(stage) {
  return stage === 'finished_win' || stage === 'finished_loss';
}
