import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/theme.css'
import App from './App.jsx'
import { MusicProvider } from './music/MusicContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MusicProvider>
      <App />
    </MusicProvider>
  </StrictMode>,
)
