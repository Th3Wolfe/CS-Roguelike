// Mods vêm sempre na perspectiva CT (positivo = vantagem CT), espelhando
// systems/tactics.py::CT_MATCHUP_MOD. Pra tática T, inverte — igual à
// lógica do backend (get_tactic_modifier).
export function edgeFor(matchups, side, tacKey, oppKey) {
  const ctKey = side === 'ct' ? tacKey : oppKey;
  const tKey  = side === 'ct' ? oppKey : tacKey;
  const entry = matchups?.find((m) => m.ct === ctKey && m.t === tKey);
  if (!entry) return 0;
  return side === 'ct' ? entry.mod : -entry.mod;
}

export function cleanTacticLabel(label) {
  return (label || '').replace(/^\S+\s/, '');
}

export function tacticEmoji(v) {
  return v?.emoji || (v?.label || '').split(' ')[0] || '';
}
