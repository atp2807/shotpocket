import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class MemesApi extends BaseApiClient {
  getMeme(id) {
    return this.get(API_ROUTES.MEMES.DETAIL(id));
  }

  getSimilar(id) {
    return this.get(API_ROUTES.MEMES.SIMILAR(id));
  }
}

export const memesApi = new MemesApi();
