import { Link } from 'react-router-dom';
import './Footer.css';

// 법무 페이지 진입점 — 신고/개인정보처리방침/이용약관 discoverability.
export default function Footer() {
  return (
    <footer className="app-footer">
      <Link to="/report" className="app-footer__link">
        신고·삭제요청
      </Link>
      <span className="app-footer__dot">·</span>
      <Link to="/privacy" className="app-footer__link">
        개인정보처리방침
      </Link>
      <span className="app-footer__dot">·</span>
      <Link to="/terms" className="app-footer__link">
        이용약관
      </Link>
    </footer>
  );
}
