import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { REPORT_REASON } from '@shotpocket/shared';
import { reportsApi } from '../services/api/reports.js';
import { showToast } from '../components/common/Toast.js';
import { logger } from '../utils/logger.js';
import './ReportPage.css';

const REASON_OPTIONS = [
  { code: REPORT_REASON.COPYRIGHT, label: '저작권' },
  { code: REPORT_REASON.PORTRAIT_RIGHT, label: '초상권' },
  { code: REPORT_REASON.NSFW, label: '음란' },
  { code: REPORT_REASON.HATE, label: '혐오' },
  { code: REPORT_REASON.SPAM, label: '스팸' },
  { code: REPORT_REASON.ETC, label: '기타' },
];

// 짤 상세 URL(또는 UUID)에서 meme_id 를 추출한다.
function extractMemeId(input) {
  const trimmed = (input || '').trim();
  const match = trimmed.match(
    /([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/,
  );
  return match ? match[1] : null;
}

// 신고/삭제요청 접수 페이지 — 계정·이메일 없이 폼 제출만으로 접수(ops.report DB 적재).
// 접수 즉시 해당 짤은 자동 비공개 처리된다(무인 원칙).
export default function ReportPage() {
  const [url, setUrl] = useState('');
  const [reasonCd, setReasonCd] = useState(REPORT_REASON.COPYRIGHT);
  const [detail, setDetail] = useState('');
  const [contact, setContact] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const memeId = extractMemeId(url);
    if (!memeId) {
      showToast('짤 상세 페이지 주소를 정확히 붙여넣어 주세요', 'danger');
      return;
    }
    setSubmitting(true);
    try {
      await reportsApi.createReport({
        memeId,
        reasonCd,
        detail: detail.trim(),
        contact: contact.trim(),
      });
      setDone(true);
    } catch (err) {
      logger.error('신고 접수 실패', err);
      showToast('접수에 실패했어요. 주소를 확인하고 다시 시도해 주세요', 'danger');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="report-page">
      <div className="report-page__head">
        <Link to="/" className="report-page__back" aria-label="피드로">
          <ArrowLeft size={22} />
        </Link>
        <h1 className="report-page__title">신고 · 삭제 요청</h1>
      </div>

      <p className="report-page__desc">
        저작권·초상권 등의 사유로 특정 짤의 삭제를 원하시면 아래 양식으로
        접수해 주세요. <strong>접수 즉시 해당 짤은 자동으로 비공개 처리</strong>
        됩니다. 별도 이메일 회신은 드리지 않으며, 연락처를 남기시면 처리
        확인 목적으로만 사용합니다.
      </p>

      {done ? (
        <div className="report-page__done">
          <p>접수됐어요. 해당 짤은 비공개 처리됩니다.</p>
          <Link to="/" className="btn btn--primary btn--small">
            피드로 돌아가기
          </Link>
        </div>
      ) : (
        <form className="report-page__form" onSubmit={handleSubmit}>
          <label className="report-page__field">
            <span className="report-page__label">신고할 짤 주소</span>
            <input
              className="report-page__input"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://shotpocket.sitos.me/meme/..."
              required
            />
          </label>

          <fieldset className="report-page__reasons">
            <legend className="report-page__label">사유</legend>
            <div className="report-page__chips">
              {REASON_OPTIONS.map((opt) => (
                <label
                  key={opt.code}
                  className={
                    reasonCd === opt.code
                      ? 'chip chip--active'
                      : 'chip'
                  }
                >
                  <input
                    type="radio"
                    name="reason"
                    value={opt.code}
                    checked={reasonCd === opt.code}
                    onChange={() => setReasonCd(opt.code)}
                    className="report-page__radio"
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="report-page__field">
            <span className="report-page__label">상세 내용 (선택)</span>
            <textarea
              className="report-page__textarea"
              value={detail}
              onChange={(e) => setDetail(e.target.value)}
              rows={4}
              maxLength={2000}
              placeholder="권리 관계, 원본 출처 등 참고할 내용을 적어주세요."
            />
          </label>

          <label className="report-page__field">
            <span className="report-page__label">연락처 (선택)</span>
            <input
              className="report-page__input"
              type="text"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              placeholder="이메일 등 — 처리 확인이 필요할 때만"
              maxLength={256}
            />
          </label>

          <button
            type="submit"
            className="btn btn--primary report-page__submit"
            disabled={submitting}
          >
            {submitting ? '접수 중…' : '접수하기'}
          </button>
        </form>
      )}
    </main>
  );
}
