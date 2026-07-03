import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class FeedApi extends BaseApiClient {
  // sort: recommended(기본) | today | rising | new. cursor 는 keyset 페이지네이션용.
  getFeed(cursor, sort) {
    const params = {};
    if (cursor) {
      params.cursor = cursor;
    }
    if (sort && sort !== 'recommended') {
      params.sort = sort;
    }
    return this.get(API_ROUTES.FEED.LIST, {
      params: Object.keys(params).length ? params : undefined,
    });
  }
}

export const feedApi = new FeedApi();
