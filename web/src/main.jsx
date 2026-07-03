import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

import './components/theme/colors.css';
import './components/theme/design-tokens.css';
import './components/theme/typography.css';
import './components/common/CommonStyles.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
