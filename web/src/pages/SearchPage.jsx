import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search, ArrowLeft } from 'lucide-react';
import {
  MEDIA_TYPE,
  EMOTION_LABEL,
  SITUATION_LABEL,
} from '@shotpocket/shared';
import { searchApi } from '../services/api/search.js';
import { feedApi } from '../services/api/feed.js';
import {
  getRecentSearches,
  pushRecentSearch,
} from '../utils/searchHistory.js';
import { showToast } from '../components/common/Toast.js';
import { logger } from '../utils/logger.js';
import './SearchPage.css';

const EMOTION_CHIPS = Object.values(EMOTION_LABEL);
const SITUATION_CHIPS = Object.values(SITUATION_LABEL);

// 검색/탐색 그리드 셀 — 결과 그리드·전체보기(최신순) 그리드가 공유.
function MemeGridCell({ meme }) {
  return (
    <Link to={`/meme/${meme.id}`} className="search-cell">
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
  );
}

// 의미 검색. 상단 고정 검색바 + 최근/카테고리 칩 + masonry 결과 + 무한스크롤.
// 태그(쿼리) 없는 기본 상태 = 전체보기(최신순 그리드, 인스타 탐색 느낌).
export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [phase, setPhase] = useState('idle'); // idle | loading | ready | error
  const [recent, setRecent] = useState(() => getRecentSearches());

  // idle(태그 없음) 상태의 전체보기 — 최신순 무한 그리드.
  const [exploreItems, setExploreItems] = useState([]);

  const termRef = useRef('');
  const pageRef = useRef(1);
  const totalRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(false);
  const inputRef = useRef(null);
  const sentinelRef = useRef(null);

  const exploreCursorRef = useRef(undefined);
  const exploreLoadingRef = useRef(false);
  const exploreHasMoreRef = useRef(true);
  const exploreSentinelRef = useRef(null);

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

  // URL ?q= 로 진입(상세 페이지의 태그 클릭 등) 시 자동 검색.
  useEffect(() => {
    const q = searchParams.get('q');
    if (q && q.trim()) {
      startSearch(q);
    }
    // 최초 마운트 1회만 — startSearch 는 안정 콜백이라 의존성 누락이 아니다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 전체보기(태그 없음) — 최신순 무한 그리드. idle 상태에서만 채운다.
  const loadExploreMore = useCallback(async () => {
    if (exploreLoadingRef.current || !exploreHasMoreRef.current) {
      return;
    }
    exploreLoadingRef.current = true;
    try {
      const res = await feedApi.getFeed(exploreCursorRef.current, 'new');
      const items = (res && res.items) || [];
      if (items.length > 0) {
        setExploreItems((prev) => [...prev, ...items]);
      }
      const next = (res && res.next_cursor) || null;
      exploreCursorRef.current = next || undefined;
      exploreHasMoreRef.current = Boolean(next);
    } catch (err) {
      logger.error('전체보기 로드 실패', err);
      exploreHasMoreRef.current = false;
    } finally {
      exploreLoadingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (phase === 'idle' && exploreItems.length === 0) {
      loadExploreMore();
    }
  }, [phase, exploreItems.length, loadExploreMore]);

  useEffect(() => {
    const node = exploreSentinelRef.current;
    if (!node || phase !== 'idle') {
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadExploreMore();
          }
        });
      },
      { rootMargin: '240px' },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [phase, exploreItems.length, loadExploreMore]);

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
        <>
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

        <section className="search-suggest__block">
          <h2 className="search-suggest__title">전체보기 · 최신순</h2>
          <div className="search-grid">
            {exploreItems.map((meme) => (
              <MemeGridCell key={meme.id} meme={meme} />
            ))}
          </div>
          <div
            ref={exploreSentinelRef}
            className="search-sentinel"
            aria-hidden="true"
          />
        </section>
        </>
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
              <MemeGridCell key={meme.id} meme={meme} />
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
