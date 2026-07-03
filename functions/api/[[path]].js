// Cloudflare Pages Functions — /api/* 를 백엔드로 프록시.
// 웹과 API 가 같은 오리진이 되어 CORS·VITE_API_BASE_URL 빌드 변수가 불필요해진다.
// 미디어(/media)는 여기로 태우지 않는다 — API 가 절대 URL(MEDIA_BASE_URL)을 내려
// 이미지 트래픽은 nginx+Cloudflare 캐시로 직행 (Functions 호출량 절약).
const API_ORIGIN = 'https://shotpocket-api.sitos.me';

export async function onRequest({ request }) {
  const url = new URL(request.url);
  const target = API_ORIGIN + url.pathname + url.search;
  const resp = await fetch(target, {
    method: request.method,
    headers: request.headers,
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
  });
  return resp;
}
