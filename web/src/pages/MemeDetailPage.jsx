import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { REPORT_REASON } from '@shotpocket/shared';
import MemeCard from '../components/meme/MemeCard.jsx';
import ActionBar from '../components/meme/ActionBar.jsx';
import { memesApi } from '../services/api/memes.js';
import { reportsApi } from '../services/api/reports.js';
import { logger } from '../utils/logger.js';
import './MemeDetailPage.css';

// 짤 상세 스켈레톤. memesApi(상세 + 유사) 호출, 신고는 reportsApi.
export default function MemeDetailPage() {
  const { id } = useParams();
  const [meme, setMeme] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [phase, setPhase] = useState('loading'); // loading | ready | error

  useEffect(() => {
    let active = true;
    setPhase('loading');
    Promise.all([memesApi.getMeme(id), memesApi.getSimilar(id)])
      .then(([detail, sim]) => {
        if (!active) {
          return;
        }
        setMeme(detail || null);
        setSimilar((sim && sim.items) || []);
        setPhase('ready');
      })
      .catch((err) => {
        logger.error('상세 로드 실패', err);
        if (active) {
          setPhase('error');
        }
      });
    return () => {
      active = false;
    };
  }, [id]);

  const handleReport = async (memeId) => {
    try {
      await reportsApi.createReport({ memeId, reasonCd: REPORT_REASON.ETC });
      logger.info('신고 접수', memeId);
    } catch (err) {
      logger.error('신고 실패', err);
    }
  };

  if (phase === 'loading') {
    return (
      <main className="detail-page">
        <div className="detail-stage">
          <MemeCard meme={null} />
        </div>
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

  return (
    <main className="detail-page">
      <div className="detail-stage">
        <MemeCard meme={meme} />
        <div className="detail-actions">
          <ActionBar memeId={meme.id} onReport={handleReport} />
        </div>
      </div>

      {similar.length > 0 ? (
        <section className="detail-similar">
          <h2 className="detail-similar__title">비슷한 짤</h2>
          <div className="detail-similar__grid">
            {similar.map((item) => (
              <Link
                key={item.id}
                to={`/meme/${item.id}`}
                className="detail-similar__cell"
              >
                <MemeCard meme={item} />
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
