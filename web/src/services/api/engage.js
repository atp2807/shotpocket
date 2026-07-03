import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class EngageApi extends BaseApiClient {
  like(id) {
    return this.post(API_ROUTES.MEMES.LIKES(id));
  }

  countDownload(id) {
    return this.post(API_ROUTES.MEMES.DOWNLOADS(id));
  }
}

export const engageApi = new EngageApi();
