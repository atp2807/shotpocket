import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class SearchApi extends BaseApiClient {
  search(q, page = 1) {
    return this.get(API_ROUTES.SEARCH.QUERY, { params: { q, page } });
  }
}

export const searchApi = new SearchApi();
