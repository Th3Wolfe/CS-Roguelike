import CampaignCard from './CampaignCard';
import LastResultCard from './LastResultCard';
import NextMatchupCard from './NextMatchupCard';
import './hub.css';

export default function HubInfoStrip({ team, campaign, bracket, lastWinProbability }) {
  return (
    <div className="hub-info-strip">
      <CampaignCard campaign={campaign} />
      <LastResultCard campaign={campaign} lastWinProbability={lastWinProbability} />
      <NextMatchupCard team={team} campaign={campaign} bracket={bracket} />
    </div>
  );
}
