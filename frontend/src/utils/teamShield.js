// Mesma lógica de slugify usada em ui/index.html (ver systems/team_factory.py
// TEAM_NAMES pra a lista de adversários NPC e ui/static/shields/README.md
// pros nomes de arquivo esperados).
export function slugifyTeamName(name) {
  return (name || '')
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // remove acentos
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function shieldUrl(name) {
  return `/ui/static/shields/${slugifyTeamName(name)}.png`;
}
