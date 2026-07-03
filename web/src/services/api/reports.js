import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class ReportsApi extends BaseApiClient {
  // 신고 접수. 계약: { meme_id, reason_cd, detail?, contact? }
  createReport({ memeId, reasonCd, detail, contact }) {
    return this.post(API_ROUTES.REPORTS.CREATE, {
      body: {
        meme_id: memeId,
        reason_cd: reasonCd,
        detail: detail || undefined,
        contact: contact || undefined,
      },
    });
  }
}

export const reportsApi = new ReportsApi();
