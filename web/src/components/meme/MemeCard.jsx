import { MEDIA_TYPE } from '@shotpocket/shared';
import './MemeCard.css';

// media_type_cd 가 LOOP 면 자동재생 무한루프 video, STILL 이면 img.
export default function MemeCard({ meme }) {
  if (!meme) {
    return <div className="meme-card meme-card--empty skeleton" />;
  }

  const isLoop = meme.media_type_cd === MEDIA_TYPE.LOOP;

  return (
    <article className="meme-card">
      {isLoop ? (
        <video
          className="meme-card__media"
          src={meme.media_url}
          poster={meme.thumb_url}
          autoPlay
          muted
          loop
          playsInline
        />
      ) : (
        <img
          className="meme-card__media"
          src={meme.media_url}
          alt={meme.caption || '짤'}
          loading="lazy"
        />
      )}
      {meme.caption ? <p className="meme-card__caption">{meme.caption}</p> : null}
    </article>
  );
}
