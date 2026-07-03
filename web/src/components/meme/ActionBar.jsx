import { useState } from 'react';
import { Heart, Download, Share2, Flag } from 'lucide-react';
import { ERROR_CODES } from '@shotpocket/shared';
import { engageApi } from '../../services/api/engage.js';
import { showToast } from '../common/Toast.js';
import { recordEngagement, markLiked, isLiked } from '../../utils/personalize.js';
import { logger } from '../../utils/logger.js';
import ReportModal from './ReportModal.jsx';
import './ActionBar.css';

function formatCount(n) {
  const v = Number(n) || 0;
  if (v >= 10000) {
    return `${Math.round(v / 1000)}k`;
  }
  if (v >= 1000) {
    return `${(v / 1000).toFixed(1)}k`;
  }
  return String(v);
}

// orientation: 'vertical'(피드) | 'horizontal'(상세)
export default function ActionBar({ meme, orientation = 'vertical' }) {
  const memeId = meme && meme.id;
  const [liked, setLiked] = useState(() => isLiked(memeId));
  const [likeCount, setLikeCount] = useState(() => Number(meme && meme.like_cnt) || 0);
  const [downloadCount, setDownloadCount] = useState(
    () => Number(meme && meme.download_cnt) || 0,
  );
  const [busy, setBusy] = useState(false);
  const [reporting, setReporting] = useState(false);

  const handleLike = async () => {
    if (busy) {
      return;
    }
    if (liked) {
      showToast('이미 반영됨');
      return;
    }
    setBusy(true);
    // 낙관적 반영
    setLiked(true);
    setLikeCount((c) => c + 1);
    try {
      await engageApi.like(memeId);
      markLiked(memeId);
      recordEngagement(memeId);
    } catch (err) {
      if (err && err.errorCode === ERROR_CODES.ENGAGE_001.code) {
        // 이미 좋아요된 상태 — 낙관 반영 유지, 카운트는 원복
        markLiked(memeId);
        setLikeCount((c) => Math.max(0, c - 1));
        showToast('이미 반영됨');
      } else {
        // 실패 — 낙관 반영 롤백
        setLiked(false);
        setLikeCount((c) => Math.max(0, c - 1));
        logger.error('좋아요 실패', err);
        showToast('좋아요에 실패했어요', 'danger');
      }
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async () => {
    try {
      const res = await engageApi.countDownload(memeId);
      const url = res && res.download_url;
      if (url) {
        const a = document.createElement('a');
        a.href = url;
        a.download = '';
        a.rel = 'noopener';
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
      setDownloadCount((c) => c + 1);
      recordEngagement(memeId);
      showToast('짤을 저장했어요', 'success');
    } catch (err) {
      logger.error('다운로드 실패', err);
      showToast('다운로드에 실패했어요', 'danger');
    }
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/meme/${memeId}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: 'ShotPocket', url });
        return;
      }
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
        showToast('링크를 복사했어요', 'success');
        return;
      }
      showToast('공유를 지원하지 않는 환경이에요');
    } catch (err) {
      // 사용자가 공유 시트를 닫은 경우 등 — 조용히 무시
      logger.warn('공유 취소/실패', err);
    }
  };

  const barClass =
    orientation === 'horizontal'
      ? 'action-bar action-bar--horizontal'
      : 'action-bar';

  return (
    <div className={barClass}>
      <div className="action-bar__item">
        <button
          type="button"
          className={
            liked
              ? 'action-bar__btn action-bar__btn--active'
              : 'action-bar__btn'
          }
          onClick={handleLike}
          aria-pressed={liked}
          aria-label="좋아요"
        >
          <Heart size={22} fill={liked ? 'currentColor' : 'none'} />
        </button>
        <span className="action-bar__count">{formatCount(likeCount)}</span>
      </div>

      <div className="action-bar__item">
        <button
          type="button"
          className="action-bar__btn"
          onClick={handleDownload}
          aria-label="다운로드"
        >
          <Download size={22} />
        </button>
        <span className="action-bar__count">{formatCount(downloadCount)}</span>
      </div>

      <div className="action-bar__item">
        <button
          type="button"
          className="action-bar__btn"
          onClick={handleShare}
          aria-label="공유"
        >
          <Share2 size={22} />
        </button>
      </div>

      <div className="action-bar__item">
        <button
          type="button"
          className="action-bar__btn"
          onClick={() => setReporting(true)}
          aria-label="신고"
        >
          <Flag size={22} />
        </button>
      </div>

      {reporting ? (
        <ReportModal memeId={memeId} onClose={() => setReporting(false)} />
      ) : null}
    </div>
  );
}
