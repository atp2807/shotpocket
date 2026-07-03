import { BaseApiClient } from './api_client.js';
import { API_ROUTES } from '../../config/api.js';

class EngageApi extends BaseApiClient {
  like(id) {
    return this.post(API_ROUTES.MEMES.LIKES(id));
  }

  countDownload(id) {
    return this.post(API_ROUTES.MEMES.DOWNLOADS(id));
  }

  // 조회수 집계. 뷰는 실패 개념 없음(중복도 200) — 호출부에서 실패는 무시한다.
  countView(id) {
    return this.post(API_ROUTES.MEMES.VIEWS(id));
  }
}

export const engageApi = new EngageApi();
