import { API_CONFIG } from '../../config/api.js';
import { logger } from '../../utils/logger.js';

// 비정상 응답을 표준 에러로 표현. 서버 에러 형식: { error_code, message }
export class ApiError extends Error {
  constructor(errorCode, message, status) {
    super(message || '요청 처리에 실패했습니다.');
    this.name = 'ApiError';
    this.errorCode = errorCode || 'COMMON_002';
    this.status = status;
  }
}

// 모든 API 서비스의 베이스 클래스. 컴포넌트는 이 클래스 상속 클래스로만 호출한다.
// 인증/토큰 개념 없음 (계정 없는 제품).
export class BaseApiClient {
  constructor(baseUrl = API_CONFIG.BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async request(method, path, { params, body, timeoutMs = API_CONFIG.TIMEOUT_MS } = {}) {
    const url = this.#buildUrl(path, params);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: body != null ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      const payload = await this.#parseBody(response);

      if (!response.ok) {
        const errorCode = (payload && payload.error_code) || 'COMMON_002';
        const message = (payload && payload.message) || '요청 처리에 실패했습니다.';
        throw new ApiError(errorCode, message, response.status);
      }

      return payload;
    } catch (err) {
      if (err instanceof ApiError) {
        throw err;
      }
      if (err && err.name === 'AbortError') {
        logger.error('API 요청 타임아웃', method, path);
        throw new ApiError('COMMON_002', '요청 시간이 초과되었습니다.', 0);
      }
      logger.error('API 요청 실패', method, path, err);
      throw new ApiError('COMMON_002', '네트워크 오류가 발생했습니다.', 0);
    } finally {
      clearTimeout(timer);
    }
  }

  get(path, options) {
    return this.request('GET', path, options);
  }

  post(path, options) {
    return this.request('POST', path, options);
  }

  #buildUrl(path, params) {
    const base = `${this.baseUrl}${path}`;
    if (!params) {
      return base;
    }
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, String(value));
      }
    });
    const qs = query.toString();
    return qs ? `${base}?${qs}` : base;
  }

  async #parseBody(response) {
    const text = await response.text();
    if (!text) {
      return null;
    }
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  }
}
