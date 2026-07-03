import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class ReportsApi extends BaseApiClient {
  createReport({ memeId, reasonCd, detail }) {
    return this.post(API_ROUTES.REPORTS.CREATE, {
      body: { meme_id: memeId, reason_cd: reasonCd, detail },
    });
  }
}

export const reportsApi = new ReportsApi();
