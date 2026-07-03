import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import MemeCard from '../components/meme/MemeCard.jsx';
import ActionBar from '../components/meme/ActionBar.jsx';
import { feedApi } from '../services/api/feed.js';
import { logger } from '../utils/logger.js';
import './FeedPage.css';

// 세로 무한 스와이프 피드 스켈레톤. 실제 feedApi 호출 + 로딩/에러 상태.
export default function FeedPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [phase, setPhase] = useState('loading'); // loading | ready | error

  useEffect(() => {
    let active = true;
    feedApi
      .getFeed()
      .then((res) => {
        if (!active) {
          return;
        }
        setItems((res && res.items) || []);
        setPhase('ready');
      })
      .catch((err) => {
        logger.error('피드 로드 실패', err);
        if (active) {
          setPhase('error');
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const handleReport = useCallback((memeId) => {
    logger.info('신고 요청', memeId);
  }, []);

  if (phase === 'loading') {
    return (
      <main className="feed-page">
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
        <p className="feed-message">피드를 불러오지 못했어요.</p>
      </main>
    );
  }

  if (items.length === 0) {
    return (
      <main className="feed-page feed-page--message">
        <p className="feed-message">아직 짤이 없어요.</p>
      </main>
    );
  }

  return (
    <main className="feed-page">
      <section className="feed-scroller">
        {items.map((meme) => (
          <div key={meme.id} className="feed-slide">
            <MemeCard meme={meme} />
            <div className="feed-slide__actions">
              <ActionBar memeId={meme.id} onReport={handleReport} />
            </div>
            <button
              type="button"
              className="feed-slide__open"
              onClick={() => navigate(`/meme/${meme.id}`)}
              aria-label="상세 보기"
            />
          </div>
        ))}
      </section>
    </main>
  );
}
