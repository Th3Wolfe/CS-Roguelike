export const ROLE_ORDER = ['IGL', 'AWPer', 'Entry Fragger', 'Support', 'Lurker'];

export const ROLE_EMOJI = {
  IGL: '🧠',
  AWPer: '🔭',
  'Entry Fragger': '💥',
  Support: '🛡️',
  Lurker: '🐍',
};

// Cor de destaque de cada função (usada no badge do pool card).
export const ROLE_COLOR = {
  IGL:             { color: 'var(--color-primary)', borderColor: 'rgba(246,179,51,.35)' },
  AWPer:           { color: 'var(--color-success)', borderColor: 'rgba(54,217,120,.35)' },
  'Entry Fragger': { color: 'var(--color-danger)',  borderColor: 'rgba(241,76,76,.35)' },
  Support:         { color: 'var(--color-success)', borderColor: 'rgba(54,217,120,.35)' },
  Lurker:          { color: 'var(--color-purple)',  borderColor: 'rgba(163,108,255,.35)' },
};

// Quais das 5 estatísticas mostradas no card são "chave" pra cada função
// (ficam destacadas em verde).
export const KEY_STATS = {
  IGL: ['kast', 'impact', 'rating'],
  AWPer: ['rating', 'adr', 'impact'],
  'Entry Fragger': ['kpr', 'impact', 'rating'],
  Support: ['kast', 'rating', 'adr'],
  Lurker: ['kpr', 'kast', 'rating'],
};

export const STAT_KEYS = [
  ['rating', 'RTG'],
  ['kast', 'KAST'],
  ['impact', 'IMP'],
  ['adr', 'ADR'],
  ['kpr', 'KPR'],
];

export const FLAGS = {
  BR: '🇧🇷', UA: '🇺🇦', RU: '🇷🇺', FR: '🇫🇷', SE: '🇸🇪', DK: '🇩🇰', PL: '🇵🇱',
  CA: '🇨🇦', US: '🇺🇸', DE: '🇩🇪', UK: '🇬🇧', LV: '🇱🇻', LT: '🇱🇹', EE: '🇪🇪',
  KZ: '🇰🇿', BA: '🇧🇦', RS: '🇷🇸', NO: '🇳🇴', IL: '🇮🇱', BE: '🇧🇪', TR: '🇹🇷',
  ID: '🇮🇩', SK: '🇸🇰', FI: '🇫🇮',
};

export function flag(countryCode) {
  return FLAGS[countryCode] || '🏴';
}

// Times usados só de enfeite na "roleta" de sorteio (não tem relação com
// os times NPC reais do bracket — é puramente cosmético, pra dar a sensação
// de sorteio giratório enquanto a API responde).
export const SPIN_TEAM_NAMES = [
  'Astralis', 'fnatic', 'NiP', 'Luminosity', 'Virtus.pro',
  'Natus Vincere', 'FaZe Clan', 'Team Vitality', 'G2 Esports',
  'Team Spirit', 'FURIA', 'Heroic', 'Team Liquid', 'Cloud9',
  'BIG', 'ENCE', 'Mouz', 'Outsiders', 'The MongolZ', 'paiN Gaming',
];
