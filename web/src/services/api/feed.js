import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class FeedApi extends BaseApiClient {
  getFeed(cursor) {
    return this.get(API_ROUTES.FEED.LIST, {
      params: cursor ? { cursor } : undefined,
    });
  }
}

export const feedApi = new FeedApi();
