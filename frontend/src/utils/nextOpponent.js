// Espelha systems/campaign_manager.py: _get_paired_opponent (Swiss) e
// _get_playoff_opponent (mata-mata), usando os dados que /api/state já
// devolve em `bracket` — sem precisar de um endpoint novo no Flask.
const PLAYOFF_KEY_BY_STAGE = { playoffs_qf: 'qf', playoffs_sf: 'sf', playoffs_final: 'final' };
const PLAYOFF_LABEL_BY_STAGE = {
  playoffs_qf: 'Quartas de Final',
  playoffs_sf: 'Semifinal',
  playoffs_final: 'Grande Final',
};

function findNpcStrength(bracket, name) {
  const npc = (bracket.npc_teams || []).find((t) => t.name === name);
  return npc ? npc.strength : null;
}

export function getNextOpponentInfo({ campaign, team, bracket }) {
  if (!campaign || !team) return null;
  const stage = campaign.stage;
  bracket = bracket || {};
  const playerName = team.name;

  if (stage === 'stage1' || stage === 'stage2') {
    const pairing = (bracket.pending_pairings || [])
      .find((p) => p.a === playerName || p.b === playerName);
    if (!pairing) return null;
    const oppName = pairing.a === playerName ? pairing.b : pairing.a;
    return {
      name: oppName,
      strength: findNpcStrength(bracket, oppName),
      stageLabel: stage === 'stage1' ? 'Stage 1 — Swiss' : 'Stage 2 — Swiss',
    };
  }

  const key = PLAYOFF_KEY_BY_STAGE[stage];
  if (!key) return null; // finished_win / finished_loss — não há próxima partida

  const target = (bracket.playoff_bracket || {})[key];
  const matches = Array.isArray(target) ? target : (target ? [target] : []);
  const playerMatch = matches.find((m) => m.is_player_match);
  if (!playerMatch) return null;

  const oppName = playerMatch.a === playerName ? playerMatch.b : playerMatch.a;
  if (!oppName || oppName === '?') return null;

  return {
    name: oppName,
    strength: findNpcStrength(bracket, oppName),
    stageLabel: PLAYOFF_LABEL_BY_STAGE[stage],
  };
}
