import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import MemeCard from '../components/meme/MemeCard.jsx';
import { searchApi } from '../services/api/search.js';
import { logger } from '../utils/logger.js';
import './SearchPage.css';

// 의미 검색 스켈레톤. 실제 searchApi 호출 + 로딩/에러 상태.
export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [phase, setPhase] = useState('idle'); // idle | loading | ready | error

  const runSearch = async (event) => {
    event.preventDefault();
    const q = query.trim();
    if (!q) {
      return;
    }
    setPhase('loading');
    try {
      const res = await searchApi.search(q);
      setResults((res && res.items) || []);
      setPhase('ready');
    } catch (err) {
      logger.error('검색 실패', err);
      setPhase('error');
    }
  };

  return (
    <main className="search-page">
      <form className="search-bar" onSubmit={runSearch}>
        <Search size={18} className="search-bar__icon" />
        <input
          className="search-bar__input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="어떤 짤을 찾으세요?"
          aria-label="검색어"
        />
        <button type="submit" className="btn btn--primary btn--small">
          검색
        </button>
      </form>

      {phase === 'loading' ? (
        <p className="search-status">검색 중…</p>
      ) : null}
      {phase === 'error' ? (
        <p className="search-status">검색에 실패했어요.</p>
      ) : null}
      {phase === 'ready' && results.length === 0 ? (
        <p className="search-status">결과가 없어요.</p>
      ) : null}

      <section className="search-grid">
        {results.map((meme) => (
          <Link key={meme.id} to={`/meme/${meme.id}`} className="search-grid__cell">
            <MemeCard meme={meme} />
          </Link>
        ))}
      </section>
    </main>
  );
}
