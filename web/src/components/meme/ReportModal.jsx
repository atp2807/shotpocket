import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { REPORT_REASON } from '@shotpocket/shared';
import { reportsApi } from '../../services/api/reports.js';
import { showToast } from '../common/Toast.js';
import { logger } from '../../utils/logger.js';
import './ReportModal.css';

// 신고 사유 6종 (코드값은 공유 상수, 라벨만 한국어).
const REASON_OPTIONS = [
  { code: REPORT_REASON.COPYRIGHT, label: '저작권' },
  { code: REPORT_REASON.PORTRAIT_RIGHT, label: '초상권' },
  { code: REPORT_REASON.NSFW, label: '음란' },
  { code: REPORT_REASON.HATE, label: '혐오' },
  { code: REPORT_REASON.SPAM, label: '스팸' },
  { code: REPORT_REASON.ETC, label: '기타' },
];

export default function ReportModal({ memeId, onClose }) {
  const [reasonCd, setReasonCd] = useState(REPORT_REASON.COPYRIGHT);
  const [detail, setDetail] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitting) {
      return;
    }
    setSubmitting(true);
    try {
      await reportsApi.createReport({ memeId, reasonCd, detail: detail.trim() });
      showToast('접수됨, 해당 짤은 숨김 처리됩니다', 'success');
      onClose();
    } catch (err) {
      logger.error('신고 실패', err);
      showToast('신고 접수에 실패했어요', 'danger');
      setSubmitting(false);
    }
  };

  return (
    <div
      className="report-modal"
      role="dialog"
      aria-modal="true"
      aria-label="짤 신고"
    >
      <button
        type="button"
        className="report-modal__backdrop"
        aria-label="닫기"
        onClick={onClose}
      />
      <form className="report-modal__panel" onSubmit={handleSubmit}>
        <header className="report-modal__head">
          <h2 className="report-modal__title">신고하기</h2>
          <button
            type="button"
            className="report-modal__close"
            onClick={onClose}
            aria-label="닫기"
          >
            <X size={20} />
          </button>
        </header>

        <fieldset className="report-modal__reasons">
          <legend className="report-modal__legend">사유를 선택하세요</legend>
          {REASON_OPTIONS.map((opt) => (
            <label
              key={opt.code}
              className={
                reasonCd === opt.code
                  ? 'report-modal__reason report-modal__reason--active'
                  : 'report-modal__reason'
              }
            >
              <input
                type="radio"
                name="report-reason"
                value={opt.code}
                checked={reasonCd === opt.code}
                onChange={() => setReasonCd(opt.code)}
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </fieldset>

        <label className="report-modal__field">
          <span className="report-modal__field-label">상세 내용 (선택)</span>
          <textarea
            className="report-modal__textarea"
            value={detail}
            onChange={(e) => setDetail(e.target.value)}
            rows={3}
            maxLength={500}
            placeholder="추가로 알려주실 내용이 있다면 적어주세요."
          />
        </label>

        <button
          type="submit"
          className="btn btn--primary report-modal__submit"
          disabled={submitting}
        >
          {submitting ? '접수 중…' : '신고 접수'}
        </button>
      </form>
    </div>
  );
}
