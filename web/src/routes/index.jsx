import { createBrowserRouter } from 'react-router-dom';
import FeedPage from '../pages/FeedPage.jsx';
import SearchPage from '../pages/SearchPage.jsx';
import MemeDetailPage from '../pages/MemeDetailPage.jsx';
import NotFoundPage from '../pages/NotFoundPage.jsx';

export const router = createBrowserRouter([
  { path: '/', element: <FeedPage /> },
  { path: '/search', element: <SearchPage /> },
  { path: '/meme/:id', element: <MemeDetailPage /> },
  { path: '*', element: <NotFoundPage /> },
]);
