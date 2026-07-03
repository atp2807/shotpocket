import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import MemeCard from '../components/meme/MemeCard.jsx';
import ActionBar from '../components/meme/ActionBar.jsx';
import { feedApi } from '../services/api/feed.js';
import { memesApi } from '../services/api/memes.js';
import { pickSeedMemeId } from '../utils/personalize.js';
import { showToast } from '../components/common/Toast.js';
import { logger } from '../utils/logger.js';
import './FeedPage.css';

const SIMILAR_PER_PAGE = 3;

// 개인화 similar 아이템을 피드 아이템 사이에 고르게 끼워 넣는다.
function interleave(base, extras) {
  if (extras.length === 0) {
    return base;
  }
  const out = [...base];
  const step = Math.max(1, Math.floor(out.length / (extras.length + 1)));
  extras.forEach((item, i) => {
    const pos = Math.min(out.length, step * (i + 1) + i);
    out.splice(pos, 0, item);
  });
  return out;
}

// 세로 스냅 무한 피드. 마지막-2번째 카드 노출 시 다음 페이지를 당겨오고,
// 화면에 들어온 카드의 video 만 재생한다(off-screen pause).
export default function FeedPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [phase, setPhase] = useState('loading'); // loading | ready | error | empty
  const [activeId, setActiveId] = useState(null);

  const seenRef = useRef(new Set());
  const cursorRef = useRef(undefined);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const slideRefs = useRef(new Map());
  const startedRef = useRef(false);

  const mergeNew = useCallback((incoming) => {
    const fresh = [];
    incoming.forEach((m) => {
      if (m && m.id && !seenRef.current.has(m.id)) {
        seenRef.current.add(m.id);
        fresh.push(m);
      }
    });
    return fresh;
  }, []);

  const loadMore = useCallback(async () => {
    if (loadingRef.current || !hasMoreRef.current) {
      return;
    }
    loadingRef.current = true;
    try {
      const res = await feedApi.getFeed(cursorRef.current);
      const pageItems = mergeNew((res && res.items) || []);

      // 로컬 개인화: 최근 engaged 짤의 similar 를 2~3개 자연스럽게 섞는다.
      let mixed = pageItems;
      const seed = pickSeedMemeId();
      if (seed) {
        try {
          const sim = await memesApi.getSimilar(seed);
          const simItems = mergeNew(
            ((sim && sim.items) || []).slice(0, SIMILAR_PER_PAGE),
          );
          mixed = interleave(pageItems, simItems);
        } catch (err) {
          logger.warn('개인화 similar 로드 실패', err);
        }
      }

      if (mixed.length > 0) {
        setItems((prev) => {
          const next = [...prev, ...mixed];
          setActiveId((cur) => cur || (next[0] && next[0].id) || null);
          return next;
        });
      }

      const next = (res && res.next_cursor) || null;
      cursorRef.current = next || undefined;
      hasMoreRef.current = Boolean(next);

      setPhase((prev) => {
        if (mixed.length === 0 && prev === 'loading') {
          return 'empty';
        }
        return 'ready';
      });
    } catch (err) {
      logger.error('피드 로드 실패', err);
      setPhase((prev) => {
        if (prev === 'loading') {
          return 'error';
        }
        showToast('피드를 더 불러오지 못했어요', 'danger');
        return prev;
      });
      hasMoreRef.current = false;
    } finally {
      loadingRef.current = false;
    }
  }, [mergeNew]);

  // 최초 1회 로드
  useEffect(() => {
    if (startedRef.current) {
      return;
    }
    startedRef.current = true;
    loadMore();
  }, [loadMore]);

  const registerSlide = useCallback((id, el) => {
    if (el) {
      slideRefs.current.set(id, el);
    } else {
      slideRefs.current.delete(id);
    }
  }, []);

  // 재생 제어 + 페이지네이션 트리거 옵저버.
  useEffect(() => {
    if (items.length === 0) {
      return undefined;
    }
    const nodes = Array.from(slideRefs.current.values());

    // 재생 제어: 가장 많이 보이는 카드를 active 로.
    const playObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
            const id = entry.target.dataset.memeId;
            if (id) {
              setActiveId(id);
            }
          }
        });
      },
      { threshold: [0.6] },
    );

    // 페이지네이션: 마지막-2번째 카드가 보이면 다음 페이지.
    const sentinelIndex = Math.max(0, items.length - 2);
    const sentinelNode = nodes[sentinelIndex];
    const pageObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadMore();
          }
        });
      },
      { threshold: 0.1 },
    );

    nodes.forEach((node) => playObserver.observe(node));
    if (sentinelNode) {
      pageObserver.observe(sentinelNode);
    }

    return () => {
      playObserver.disconnect();
      pageObserver.disconnect();
    };
  }, [items, loadMore]);

  const topNav = (
    <nav className="feed-nav">
      <Link to="/" className="feed-nav__logo" aria-label="ShotPocket 홈">
        ShotPocket
      </Link>
      <Link to="/search" className="feed-nav__search" aria-label="검색">
        <Search size={22} />
      </Link>
    </nav>
  );

  if (phase === 'loading') {
    return (
      <main className="feed-page">
        {topNav}
        <section className="feed-scroller">
          <div className="feed-slide">
            <MemeCard meme={null} />
          </div>
        </section>
      </main>
    );
  }

  if (phase === 'error') {
    return (
      <main className="feed-page feed-page--message">
        {topNav}
        <p className="feed-message">피드를 불러오지 못했어요.</p>
        <Link to="/search" className="btn btn--ghost btn--small">
          검색으로 찾아보기
        </Link>
      </main>
    );
  }

  if (phase === 'empty' || items.length === 0) {
    return (
      <main className="feed-page feed-page--message">
        {topNav}
        <p className="feed-message">아직 짤이 없어요.</p>
      </main>
    );
  }

  return (
    <main className="feed-page">
      {topNav}
      <section className="feed-scroller">
        {items.map((meme) => (
          <div
            key={meme.id}
            className="feed-slide"
            data-meme-id={meme.id}
            ref={(el) => registerSlide(meme.id, el)}
          >
            <MemeCard meme={meme} active={activeId === meme.id} showMeta />
            <button
              type="button"
              className="feed-slide__open"
              onClick={() => navigate(`/meme/${meme.id}`)}
              aria-label="상세 보기"
            />
            <div className="feed-slide__actions">
              <ActionBar meme={meme} orientation="vertical" />
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
