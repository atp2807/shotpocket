import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import './LegalPage.css';

// 개인정보처리방침 — 계정·로그인 없는 서비스라 수집 정보가 최소화돼 있음을
// 있는 그대로 서술한다(과장·복붙 방지, 실제 구현과 일치).
export default function PrivacyPage() {
  return (
    <main className="legal-page">
      <div className="legal-page__head">
        <Link to="/" className="legal-page__back" aria-label="피드로">
          <ArrowLeft size={22} />
        </Link>
        <h1 className="legal-page__title">개인정보처리방침</h1>
      </div>

      <p className="legal-page__intro">
        ShotPocket(샷포켓)은 회원가입·로그인 없이 이용할 수 있는 서비스입니다.
        그래서 수집하는 개인정보가 거의 없습니다.
      </p>

      <section className="legal-page__section">
        <h2>1. 수집하는 정보</h2>
        <ul>
          <li>
            <strong>IP 주소 해시값</strong> — 좋아요·다운로드 중복 방지, 요청
            빈도 제한(어뷰징 방지) 목적으로만 사용합니다. 원본 IP는 저장하지
            않고 되돌릴 수 없는 해시값만 저장합니다.
          </li>
          <li>
            <strong>검색어 로그</strong> — 검색 품질 개선(어떤 짤이
            부족한지 파악) 목적으로 검색어와 결과 건수를 저장합니다.
            검색자를 식별하는 정보와 연결하지 않습니다.
          </li>
          <li>
            <strong>신고 접수 시 남기신 연락처(선택)</strong> — 신고 처리
            확인 목적으로만 사용하며, 남기지 않으셔도 신고 접수에 지장
            없습니다.
          </li>
        </ul>
      </section>

      <section className="legal-page__section">
        <h2>2. 수집하지 않는 정보</h2>
        <p>
          이름, 이메일, 전화번호 등 회원 식별 정보(회원가입 자체가 없음),
          위치정보, 기기 고유 식별자는 수집하지 않습니다.
        </p>
      </section>

      <section className="legal-page__section">
        <h2>3. 내 기기에만 저장되는 정보</h2>
        <p>
          좋아요·다운로드 기록, 최근 검색어는 이용자의 브라우저(로컬
          저장소)에만 저장되며 서버로 전송되지 않습니다. 브라우저 데이터를
          지우면 함께 삭제됩니다.
        </p>
      </section>

      <section className="legal-page__section">
        <h2>4. 쿠키 및 광고</h2>
        <p>
          현재 광고를 게재하지 않습니다. 추후 광고를 도입할 경우 광고
          사업자의 쿠키 사용에 대해 본 방침을 갱신하여 고지합니다.
        </p>
      </section>

      <section className="legal-page__section">
        <h2>5. 보관 기간</h2>
        <p>
          IP 해시·검색어 로그는 서비스 운영 목적 범위에서 보관하며, 관련
          시간대별 집계 통계는 7일 후 자동 삭제됩니다.
        </p>
      </section>

      <section className="legal-page__section">
        <h2>6. 이용자 권리 및 문의</h2>
        <p>
          자신과 관련된 정보의 열람·삭제, 콘텐츠(저작권·초상권 등) 관련
          문의는 <Link to="/report">신고 페이지</Link>를 통해 접수해
          주세요.
        </p>
      </section>

      <p className="legal-page__effective">
        시행일: 2026-07-04. 본 방침은 서비스 변경에 따라 사전 고지 후
        개정될 수 있습니다.
      </p>
    </main>
  );
}
