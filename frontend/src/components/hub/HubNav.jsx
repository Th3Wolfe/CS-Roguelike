const TABS = [
  { id: 'hub', icon: '🏠', label: 'Hub', mobileLabel: 'Hub' },
  { id: 'campeonato', icon: '🏆', label: 'Chaveamento', mobileLabel: 'Chave' },
  { id: 'roster', icon: '👥', label: 'Elenco', mobileLabel: 'Elenco' },
];

export default function HubNav({ active, onChange }) {
  return (
    <>
      <nav className="hub-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`hub-nav-tab ${active === t.id ? 'active' : ''}`}
            onClick={() => onChange(t.id)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </nav>

      <nav className="mobile-bottom-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`mobile-nav-item ${active === t.id ? 'active' : ''}`}
            onClick={() => onChange(t.id)}
          >
            <span className="mobile-nav-icon">{t.icon}</span>
            <span className="mobile-nav-label">{t.mobileLabel}</span>
          </button>
        ))}
      </nav>
    </>
  );
}
