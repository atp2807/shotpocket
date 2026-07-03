import { useEffect, useRef } from 'react';
import { MEDIA_TYPE, EMOTION_LABEL } from '@shotpocket/shared';
import './MemeCard.css';

// media_type_cd === LOOP → 자동재생 무한루프 video, STILL → img.
// active=false 면 화면 밖으로 판단해 video 를 정지한다(FeedPage IntersectionObserver 제어).
// full=true 면 STILL 원본(orig_url)을 우선 사용한다(상세 페이지 고해상).
export default function MemeCard({ meme, active = true, full = false, showMeta = false }) {
  const videoRef = useRef(null);

  const isLoop = Boolean(meme) && meme.media_type_cd === MEDIA_TYPE.LOOP;

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !isLoop) {
      return;
    }
    if (active) {
      const p = video.play();
      if (p && typeof p.catch === 'function') {
        p.catch(() => {});
      }
    } else {
      video.pause();
    }
  }, [active, isLoop]);

  if (!meme) {
    return <div className="meme-card meme-card--empty skeleton" />;
  }

  const emotionLabel = EMOTION_LABEL[meme.emotion_cd];
  const stillSrc = full ? meme.orig_url || meme.thumb_url : meme.thumb_url;

  return (
    <article className="meme-card">
      {isLoop ? (
        <video
          ref={videoRef}
          className="meme-card__media"
          src={meme.mp4_url}
          poster={meme.thumb_url}
          autoPlay={active}
          muted
          loop
          playsInline
          preload="metadata"
        />
      ) : (
        <img
          className="meme-card__media"
          src={stillSrc}
          alt={meme.caption || meme.meme_name || '짤'}
          loading="lazy"
        />
      )}

      {showMeta ? (
        <div className="meme-card__meta">
          {meme.meme_name ? (
            <p className="meme-card__name">{meme.meme_name}</p>
          ) : null}
          {meme.caption ? (
            <p className="meme-card__caption">{meme.caption}</p>
          ) : null}
          {emotionLabel || meme.situation ? (
            <div className="meme-card__tags">
              {emotionLabel ? (
                <span className="meme-card__tag">#{emotionLabel}</span>
              ) : null}
              {meme.situation ? (
                <span className="meme-card__tag">#{meme.situation}</span>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
