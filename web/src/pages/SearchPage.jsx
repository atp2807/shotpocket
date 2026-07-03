import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ArrowLeft } from 'lucide-react';
import {
  MEDIA_TYPE,
  EMOTION_LABEL,
  SITUATION_LABEL,
} from '@shotpocket/shared';
import { searchApi } from '../services/api/search.js';
import {
  getRecentSearches,
  pushRecentSearch,
} from '../utils/searchHistory.js';
import { showToast } from '../components/common/Toast.js';
import { logger } from '../utils/logger.js';
import './SearchPage.css';

const EMOTION_CHIPS = Object.values(EMOTION_LABEL);
const SITUATION_CHIPS = Object.values(SITUATION_LABEL);

// 의미 검색. 상단 고정 검색바 + 최근/카테고리 칩 + masonry 결과 + 무한스크롤.
export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [phase, setPhase] = useState('idle'); // idle | loading | ready | error
  const [recent, setRecent] = useState(() => getRecentSearches());

  const termRef = useRef('');
  const pageRef = useRef(1);
  const totalRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(false);
  const inputRef = useRef(null);
  const sentinelRef = useRef(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const runFetch = useCallback(async (q, page, append) => {
    loadingRef.current = true;
    if (!append) {
      setPhase('loading');
    }
    try {
      const res = await searchApi.search(q, page);
      const items = (res && res.items) || [];
      const total = Number(res && res.total) || 0;
      totalRef.current = total;
      pageRef.current = page;
      setResults((prev) => {
        const merged = append ? [...prev, ...items] : items;
        hasMoreRef.current = items.length > 0 && merged.length < total;
        return merged;
      });
      setPhase('ready');
    } catch (err) {
      logger.error('검색 실패', err);
      hasMoreRef.current = false;
      if (append) {
        showToast('결과를 더 불러오지 못했어요', 'danger');
      } else {
        setPhase('error');
      }
    } finally {
      loadingRef.current = false;
    }
  }, []);

  const startSearch = useCallback(
    (raw) => {
      const q = (raw || '').trim();
      if (!q) {
        return;
      }
      termRef.current = q;
      pageRef.current = 1;
      setQuery(q);
      setResults([]);
      setRecent(pushRecentSearch(q));
      if (inputRef.current) {
        inputRef.current.blur();
      }
      runFetch(q, 1, false);
    },
    [runFetch],
  );

  const loadNext = useCallback(() => {
    if (loadingRef.current || !hasMoreRef.current || !termRef.current) {
      return;
    }
    runFetch(termRef.current, pageRef.current + 1, true);
  }, [runFetch]);

  // 무한스크롤 센티넬
  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) {
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadNext();
          }
        });
      },
      { rootMargin: '240px' },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [loadNext, results.length]);

  const handleSubmit = (event) => {
    event.preventDefault();
    startSearch(query);
  };

  const showSuggestions = phase === 'idle';
  const isEmpty = phase === 'ready' && results.length === 0;

  return (
    <main className="search-page">
      <div className="search-head">
        <Link to="/" className="search-back" aria-label="피드로">
          <ArrowLeft size={22} />
        </Link>
        <form className="search-bar" onSubmit={handleSubmit} role="search">
          <Search size={18} className="search-bar__icon" />
          <input
            ref={inputRef}
            className="search-bar__input"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="어떤 짤을 찾으세요?"
            aria-label="검색어"
            autoComplete="off"
          />
          <button type="submit" className="btn btn--primary btn--small">
            검색
          </button>
        </form>
      </div>

      {showSuggestions ? (
        <div className="search-suggest">
          {recent.length > 0 ? (
            <section className="search-suggest__block">
              <h2 className="search-suggest__title">최근 검색어</h2>
              <div className="search-chips">
                {recent.map((word) => (
                  <button
                    key={`recent-${word}`}
                    type="button"
                    className="chip"
                    onClick={() => startSearch(word)}
                  >
                    {word}
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          <section className="search-suggest__block">
            <h2 className="search-suggest__title">감정으로 찾기</h2>
            <div className="search-chips">
              {EMOTION_CHIPS.map((label) => (
                <button
                  key={`emotion-${label}`}
                  type="button"
                  className="chip"
                  onClick={() => startSearch(label)}
                >
                  {label}
                </button>
              ))}
            </div>
          </section>

          <section className="search-suggest__block">
            <h2 className="search-suggest__title">상황으로 찾기</h2>
            <div className="search-chips">
              {SITUATION_CHIPS.map((label) => (
                <button
                  key={`situation-${label}`}
                  type="button"
                  className="chip"
                  onClick={() => startSearch(label)}
                >
                  {label}
                </button>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {phase === 'loading' ? (
        <div className="search-grid" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={`sk-${i}`}
              className="search-cell skeleton search-cell--skeleton"
            />
          ))}
        </div>
      ) : null}

      {phase === 'error' ? (
        <p className="search-status">
          검색에 실패했어요. 잠시 후 다시 시도해 주세요.
        </p>
      ) : null}

      {isEmpty ? (
        <div className="search-empty">
          <p className="search-empty__title">찾는 짤이 없어요</p>
          <p className="search-empty__note">
            입력하신 검색어는 자동으로 기록되어, 다음에 딱 맞는 짤을 채우는 데
            쓰여요.
          </p>
          <Link to="/" className="btn btn--primary btn--small">
            피드로 가기
          </Link>
        </div>
      ) : null}

      {phase === 'ready' && results.length > 0 ? (
        <>
          <div className="search-grid">
            {results.map((meme) => (
              <Link
                key={meme.id}
                to={`/meme/${meme.id}`}
                className="search-cell"
              >
                <img
                  className="search-cell__img"
                  src={meme.thumb_url}
                  alt={meme.caption || meme.meme_name || '짤'}
                  loading="lazy"
                />
                {meme.media_type_cd === MEDIA_TYPE.LOOP ? (
                  <span className="search-cell__badge">GIF</span>
                ) : null}
                {meme.meme_name || meme.caption ? (
                  <span className="search-cell__label">
                    {meme.meme_name || meme.caption}
                  </span>
                ) : null}
              </Link>
            ))}
          </div>
          <div
            ref={sentinelRef}
            className="search-sentinel"
            aria-hidden="true"
          />
        </>
      ) : null}
    </main>
  );
}
