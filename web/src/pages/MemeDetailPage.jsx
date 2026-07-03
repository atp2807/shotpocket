import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { EMOTION_LABEL, ERROR_CODES } from '@shotpocket/shared';
import MemeCard from '../components/meme/MemeCard.jsx';
import ActionBar from '../components/meme/ActionBar.jsx';
import { memesApi } from '../services/api/memes.js';
import { engageApi } from '../services/api/engage.js';
import { logger } from '../utils/logger.js';
import './MemeDetailPage.css';

// 짤 상세. 미디어 크게 + 메타 + 가로 ActionBar + '비슷한 짤' 가로 스크롤.
// 404(MEME_001) 는 NotFound 안내로 분기.
export default function MemeDetailPage() {
  const { id } = useParams();
  const [meme, setMeme] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [phase, setPhase] = useState('loading'); // loading | ready | notfound | error

  useEffect(() => {
    let active = true;
    setPhase('loading');
    setMeme(null);
    setSimilar([]);

    memesApi
      .getMeme(id)
      .then((detail) => {
        if (!active) {
          return;
        }
        if (!detail) {
          setPhase('notfound');
          return;
        }
        setMeme(detail);
        setPhase('ready');
        // 유사 짤은 부가 정보 — 실패해도 상세는 유지.
        memesApi
          .getSimilar(id)
          .then((sim) => {
            if (active) {
              setSimilar((sim && sim.items) || []);
            }
          })
          .catch((err) => logger.warn('유사 짤 로드 실패', err));
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        const httpStatus = err && err.status;
        const notFound =
          httpStatus === 404 || (err && err.errorCode === ERROR_CODES.MEME_001.code);
        if (notFound) {
          setPhase('notfound');
        } else {
          logger.error('상세 로드 실패', err);
          setPhase('error');
        }
      });

    return () => {
      active = false;
    };
  }, [id]);

  // 상세 진입 시 조회수 1회 집계(뷰는 실패 개념 없음 — 서버 1시간 중복 무시).
  useEffect(() => {
    if (!id) {
      return;
    }
    engageApi.countView(id).catch(() => {});
  }, [id]);

  const backBar = (
    <div className="detail-topbar">
      <Link to="/" className="detail-back" aria-label="피드로">
        <ArrowLeft size={22} />
      </Link>
    </div>
  );

  if (phase === 'loading') {
    return (
      <main className="detail-page">
        {backBar}
        <div className="detail-stage">
          <MemeCard meme={null} />
        </div>
      </main>
    );
  }

  if (phase === 'notfound') {
    return (
      <main className="detail-page detail-page--message">
        <p className="detail-message">그 짤은 사라졌어요.</p>
        <p className="detail-submessage">삭제되었거나 없는 주소예요.</p>
        <Link to="/" className="btn btn--primary btn--small">
          피드로 돌아가기
        </Link>
      </main>
    );
  }

  if (phase === 'error' || !meme) {
    return (
      <main className="detail-page detail-page--message">
        <p className="detail-message">짤을 불러오지 못했어요.</p>
        <Link to="/" className="btn btn--ghost btn--small">
          피드로 돌아가기
        </Link>
      </main>
    );
  }

  const emotionLabel = EMOTION_LABEL[meme.emotion_cd];

  return (
    <main className="detail-page">
      {backBar}

      <div className="detail-stage">
        <MemeCard meme={meme} full />
      </div>

      <section className="detail-info">
        {meme.meme_name ? (
          <h1 className="detail-info__name">{meme.meme_name}</h1>
        ) : null}
        {meme.caption ? (
          <p className="detail-info__caption">{meme.caption}</p>
        ) : null}
        {emotionLabel || meme.situation || (meme.tags && meme.tags.length > 0) ? (
          <div className="detail-info__tags">
            {emotionLabel ? (
              <Link
                to={`/search?q=${encodeURIComponent(emotionLabel)}`}
                className="detail-info__tag"
              >
                #{emotionLabel}
              </Link>
            ) : null}
            {meme.situation ? (
              <Link
                to={`/search?q=${encodeURIComponent(meme.situation)}`}
                className="detail-info__tag"
              >
                #{meme.situation}
              </Link>
            ) : null}
            {(meme.tags || []).map((tag) => (
              <Link
                key={tag}
                to={`/search?q=${encodeURIComponent(tag)}`}
                className="detail-info__tag"
              >
                #{tag}
              </Link>
            ))}
          </div>
        ) : null}
        <div className="detail-info__actions">
          <ActionBar meme={meme} orientation="horizontal" />
        </div>
      </section>

      {similar.length > 0 ? (
        <section className="detail-similar">
          <h2 className="detail-similar__title">비슷한 짤</h2>
          <div className="detail-similar__strip">
            {similar.map((item) => (
              <Link
                key={item.id}
                to={`/meme/${item.id}`}
                className="detail-similar__cell"
              >
                <img
                  className="detail-similar__img"
                  src={item.thumb_url}
                  alt={item.caption || item.meme_name || '짤'}
                  loading="lazy"
                />
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
