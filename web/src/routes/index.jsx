import { createBrowserRouter } from 'react-router-dom';
import FeedPage from '../pages/FeedPage.jsx';
import SearchPage from '../pages/SearchPage.jsx';
import MemeDetailPage from '../pages/MemeDetailPage.jsx';
import ReportPage from '../pages/ReportPage.jsx';
import PrivacyPage from '../pages/PrivacyPage.jsx';
import TermsPage from '../pages/TermsPage.jsx';
import NotFoundPage from '../pages/NotFoundPage.jsx';

export const router = createBrowserRouter([
  { path: '/', element: <FeedPage /> },
  { path: '/search', element: <SearchPage /> },
  { path: '/meme/:id', element: <MemeDetailPage /> },
  { path: '/report', element: <ReportPage /> },
  { path: '/privacy', element: <PrivacyPage /> },
  { path: '/terms', element: <TermsPage /> },
  { path: '*', element: <NotFoundPage /> },
]);
