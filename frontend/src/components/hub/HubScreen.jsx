import { useState } from 'react';
import HubTopbar from './HubTopbar';
import HubNav from './HubNav';
import HubInfoStrip from './HubInfoStrip';
import WelcomeBanner from './WelcomeBanner';
import HistoryFeed from './HistoryFeed';
import BracketPanel from './BracketPanel';
import RosterPanel from './RosterPanel';
import TacticsPanel from './TacticsPanel';
import { isStageFinished } from '../../constants/stages';
import './HubTopbar.css';

export default function HubScreen({ state, lastResult, tactics, onSelectCT, onSelectT, onPlaySeries, onBackToMenu }) {
  const [tab, setTab] = useState('hub');
  const { team, campaign, bracket } = state;
  const finished = isStageFinished(campaign?.stage);
  const hasHistory = (campaign?.history || []).length > 0;

  return (
    <div className="hub-screen">
      <HubTopbar team={team} campaign={campaign} onBackToMenu={onBackToMenu} />
      <HubNav active={tab} onChange={setTab} />

      <div className="hub-content">
        <div className="hub-inner">
          {tab === 'hub' && (
            <>
              {!hasHistory && <WelcomeBanner teamName={team?.name} />}

              <HubInfoStrip
                team={team}
                campaign={campaign}
                bracket={bracket}
                lastWinProbability={lastResult?.win_probability ?? null}
              />

              {lastResult && (
                <div style={{
                  background: 'var(--color-surface)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)', padding: '14px 18px', marginBottom: 20,
                  fontSize: '.88rem', color: 'var(--text2)',
                }}>
                  {lastResult.description}
                </div>
              )}

              {!finished && (
                <TacticsPanel
                  selectedCT={tactics.ct}
                  selectedT={tactics.t}
                  onSelectCT={onSelectCT}
                  onSelectT={onSelectT}
                  onPlay={onPlaySeries}
                />
              )}

              <HistoryFeed history={campaign?.history} />
            </>
          )}

          {tab === 'campeonato' && (
            <BracketPanel team={team} campaign={campaign} bracket={bracket} />
          )}

          {tab === 'roster' && (
            <RosterPanel team={team} />
          )}
        </div>
      </div>
    </div>
  );
}
