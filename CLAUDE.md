## LinkLore
이 프로젝트는 LinkLore MCP (llre) 로 lore(결정·삽질·교훈)와 doc(핵심 구조 문서)를 관리합니다.
- 세션 시작 시 `brief` 호출 — 미결·최근 활동·정리 후보 확인
- 결정·fix·삽질 후 `add(type='lore', ...)` 로 회귀 가드 기록
- 코드 변경 전 관련 기억 검색 — `show(file='경로')` / `show(text=...)`
- 핵심 구조 문서는 `add(type='doc')`

## 프로젝트 규칙 (모하더스 컨벤션)
1. **순수 JS + CSS만.** TypeScript·Tailwind 금지. 컴포넌트는 `.jsx`, 스타일은 순수 CSS.
2. **컴포넌트에서 fetch 직접 호출 금지.** `web/src/services/api/*.js` 의 `BaseApiClient` 상속 클래스로만 호출한다. URL 하드코딩 금지 — `@shotpocket/shared` 의 `API_ROUTES` 만 사용.
3. **`*_cd`/`status`/`emotion`/`media_type` 등 코드값 문자열 리터럴 비교 금지.** `packages/shared/categories.js` 상수를 import 해서 비교한다.
4. **`console.log` 금지.** `web/src/utils/logger.js` 를 사용한다.
5. **색상·z-index 하드코딩 금지.** `var(--token)` 만 사용하며, 토큰 정의는 `web/src/components/theme/` 에만 둔다.
6. **네이밍 규칙.**
   - DB 컬럼 접미사: `_cd`(코드) / `_ts`(타임스탬프) / `_amt`(금액) / `_cnt`(카운트) / `_url` / `_hash`.
   - Enum 값: `UPPER_SNAKE_CASE`.
   - API 경로: kebab-case 복수형, 동사 금지.
   - 목록 응답: `{ items, total, page, page_size }` (피드는 `{ items, next_cursor }`).
   - 에러 응답: `{ error_code, message }`, 코드는 `DOMAIN_NNN` 형식.
   - JS: camelCase 함수/변수, PascalCase 컴포넌트, UPPER_SNAKE_CASE 상수.
   - CSS: kebab-case 클래스, 페이지 프리픽스 스코핑(`feed-*`/`search-*`/`detail-*`), CSS 변수 `--kebab-case`.
7. **마이그레이션**은 `backend/migrations/YYYY_MM_DD_*.sql` raw SQL 로 작성한다.
8. **백엔드 API 포트는 38090.** (dev 프록시: `/api` → `http://localhost:38090`)
9. **설계 정본:** LinkLore `dc-28f124be`(시스템 설계) · `dc-535ce72e`(기능 리스트).
