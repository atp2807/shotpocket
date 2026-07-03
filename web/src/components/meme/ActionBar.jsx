import { useState } from 'react';
import { Heart, Download, Share2, Flag } from 'lucide-react';
import { engageApi } from '../../services/api/engage.js';
import { logger } from '../../utils/logger.js';
import './ActionBar.css';

// 좋아요 / 다운로드 / 공유 / 신고. engage 서비스로만 서버 호출.
export default function ActionBar({ memeId, onReport }) {
  const [liked, setLiked] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleLike = async () => {
    if (busy || liked) {
      return;
    }
    setBusy(true);
    try {
      await engageApi.like(memeId);
      setLiked(true);
    } catch (err) {
      logger.error('좋아요 실패', err);
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async () => {
    try {
      await engageApi.countDownload(memeId);
    } catch (err) {
      logger.error('다운로드 카운트 실패', err);
    }
  };

  const handleShare = async () => {
    try {
      const url = `${window.location.origin}/meme/${memeId}`;
      if (navigator.share) {
        await navigator.share({ url });
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
      }
    } catch (err) {
      logger.warn('공유 취소/실패', err);
    }
  };

  const handleReport = () => {
    if (onReport) {
      onReport(memeId);
    }
  };

  return (
    <div className="action-bar">
      <button
        type="button"
        className={liked ? 'action-bar__btn action-bar__btn--active' : 'action-bar__btn'}
        onClick={handleLike}
        aria-label="좋아요"
      >
        <Heart size={22} />
      </button>
      <button
        type="button"
        className="action-bar__btn"
        onClick={handleDownload}
        aria-label="다운로드"
      >
        <Download size={22} />
      </button>
      <button
        type="button"
        className="action-bar__btn"
        onClick={handleShare}
        aria-label="공유"
      >
        <Share2 size={22} />
      </button>
      <button
        type="button"
        className="action-bar__btn"
        onClick={handleReport}
        aria-label="신고"
      >
        <Flag size={22} />
      </button>
    </div>
  );
}
