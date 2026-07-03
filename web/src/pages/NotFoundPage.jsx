import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <main className="feed-page feed-page--message">
      <p className="feed-message">없는 페이지예요.</p>
      <Link to="/" className="btn btn--ghost btn--small">
        피드로 돌아가기
      </Link>
    </main>
  );
}
