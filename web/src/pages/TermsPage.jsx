import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import './LegalPage.css';

// 이용약관 — notice-and-takedown(신고 즉시 비공개) 운영 원칙을 명시.
export default function TermsPage() {
  return (
    <main className="legal-page">
      <div className="legal-page__head">
        <Link to="/" className="legal-page__back" aria-label="피드로">
          <ArrowLeft size={22} />
        </Link>
        <h1 className="legal-page__title">이용약관</h1>
      </div>

      <section className="legal-page__section">
        <h2>1. 서비스 소개</h2>
        <p>
          ShotPocket(샷포켓, 이하 "서비스")은 인터넷에서 널리 공유되는
          밈(짤)을 의미 기반으로 검색·탐색할 수 있도록 돕는 플랫폼입니다.
          회원가입 없이 누구나 이용할 수 있습니다.
        </p>
      </section>

      <section className="legal-page__section">
        <h2>2. 콘텐츠의 출처와 저작권</h2>
        <ul>
          <li>
            서비스에 게시된 이미지는 커뮤니티·나무위키 등 공개된 출처에서
            수집되었으며, 각 콘텐츠 상세 페이지에 원본 출처 링크를
            표기합니다.
          </li>
          <li>각 콘텐츠의 저작권은 원저작자에게 있습니다. 서비스는 저작권을 주장하지 않습니다.</li>
          <li>
            저작권자·초상권자 등 권리자가 삭제를 요청하는 경우{' '}
            <Link to="/report">신고 페이지</Link>를 통해 신고할 수 있으며,
            신고 접수 즉시 해당 콘텐츠는 비공개 처리됩니다.
          </li>
          <li>콘텐츠 이용에 따른 책임은 이용자 본인에게 있습니다.</li>
        </ul>
      </section>

      <section className="legal-page__section">
        <h2>3. 서비스 이용</h2>
        <ul>
          <li>서비스는 검색·다운로드 등 기능을 무료로 제공합니다.</li>
          <li>
            자동화된 대량 요청(과도한 크롤링 등)으로 서비스에 부담을 주는
            행위는 제한될 수 있습니다.
          </li>
          <li>허위 신고, 신고 기능 남용 행위는 제한될 수 있습니다.</li>
        </ul>
      </section>

      <section className="legal-page__section">
        <h2>4. 면책</h2>
        <ul>
          <li>서비스는 수집된 콘텐츠의 정확성·완전성을 보장하지 않습니다.</li>
          <li>
            콘텐츠 관련 분쟁은 원저작자와 이용자 간의 문제이며, 서비스는
            신고 즉시 비공개 처리하는 절차로 대응합니다.
          </li>
          <li>서비스는 사전 고지 후 언제든 변경·중단될 수 있습니다.</li>
        </ul>
      </section>

      <section className="legal-page__section">
        <h2>5. 약관 변경</h2>
        <p>
          본 약관은 사전 고지 후 개정될 수 있으며, 개정 후에도 서비스를
          계속 이용하는 경우 변경된 약관에 동의한 것으로 봅니다.
        </p>
      </section>

      <p className="legal-page__effective">시행일: 2026-07-04</p>
    </main>
  );
}
