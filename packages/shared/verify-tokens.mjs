#!/usr/bin/env node
// 디자인 토큰 정합성 검증 — design-tokens.js(크로스플랫폼 단일 소스, 모바일 RN이
// 그대로 import 할 값)와 web/src/components/theme/*.css(웹 렌더용 사본) 값이
// 어긋나면(드리프트) 실패한다. 웹 CSS는 손으로 값을 옮겨 적은 것이라 리뷰 없이도
// 갈릴 수 있다 — 모바일이 같은 JS를 참조하기 시작하면 두 플랫폼 시각이 벌어진다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { COLORS, SPACING, RADIUS, SHADOW, TYPOGRAPHY, Z_INDEX } from './design-tokens.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const themeDir = path.join(__dirname, '..', '..', 'web', 'src', 'components', 'theme');

function readCssVars(file) {
  const text = readFileSync(path.join(themeDir, file), 'utf8');
  const vars = {};
  for (const m of text.matchAll(/--([\w-]+):\s*([^;]+);/g)) {
    vars[m[1]] = m[2].trim();
  }
  return vars;
}

const norm = (s) => String(s ?? '').replace(/\s+/g, ' ').trim().toLowerCase();
const failures = [];

function check(label, expected, actual) {
  if (norm(expected) !== norm(actual)) {
    failures.push(`${label}: JS="${expected}" CSS="${actual}"`);
  }
}

const colorVars = readCssVars('colors.css');
const tokenVars = readCssVars('design-tokens.css');
const typoVars = readCssVars('typography.css');

// 1) primitive 색상
check('gray-900', COLORS.gray900, colorVars['gray-900']);
check('gray-800', COLORS.gray800, colorVars['gray-800']);
check('gray-700', COLORS.gray700, colorVars['gray-700']);
check('gray-600', COLORS.gray600, colorVars['gray-600']);
check('gray-500', COLORS.gray500, colorVars['gray-500']);
check('gray-400', COLORS.gray400, colorVars['gray-400']);
check('gray-300', COLORS.gray300, colorVars['gray-300']);
check('gray-200', COLORS.gray200, colorVars['gray-200']);
check('gray-100', COLORS.gray100, colorVars['gray-100']);
check('gray-50', COLORS.gray50, colorVars['gray-50']);
check('brand-primary', COLORS.brandPrimary, colorVars['brand-primary']);
check('brand-primary-strong', COLORS.brandPrimaryStrong, colorVars['brand-primary-strong']);
check('brand-primary-soft', COLORS.brandPrimarySoft, colorVars['brand-primary-soft']);
check('accent', COLORS.accent, colorVars['accent']);
check('accent-strong', COLORS.accentStrong, colorVars['accent-strong']);
check('color-danger', COLORS.danger, colorVars['color-danger']);
check('color-success', COLORS.success, colorVars['color-success']);

// 2) semantic 색상 — JS 내부 자기정합성(CSS 는 var() 참조라 primitive만 맞으면 자동 일치)
check('surfaceBase == gray900', COLORS.gray900, COLORS.surfaceBase);
check('surfaceRaised == gray800', COLORS.gray800, COLORS.surfaceRaised);
check('textPrimary == gray50', COLORS.gray50, COLORS.textPrimary);
check('textMuted == gray200', COLORS.gray200, COLORS.textMuted);
check('borderSoft == gray600', COLORS.gray600, COLORS.borderSoft);

// 3) spacing / radius / shadow / z-index / typography
for (const [k, v] of Object.entries(SPACING)) check(`spacing-${k}`, v, tokenVars[`spacing-${k}`]);
check('radius-sm', RADIUS.sm, tokenVars['radius-sm']);
check('radius-base', RADIUS.base, tokenVars['radius-base']);
check('radius-lg', RADIUS.lg, tokenVars['radius-lg']);
check('radius-full', RADIUS.full, tokenVars['radius-full']);
check('shadow-base', SHADOW.base, tokenVars['shadow-base']);
check('shadow-raised', SHADOW.raised, tokenVars['shadow-raised']);
check('z-nav', Z_INDEX.nav, tokenVars['z-nav']);
check('z-overlay', Z_INDEX.overlay, tokenVars['z-overlay']);
check('z-modal', Z_INDEX.modal, tokenVars['z-modal']);
check('z-toast', Z_INDEX.toast, tokenVars['z-toast']);
check('font-body', TYPOGRAPHY.fontBody, tokenVars['font-body']);
check('font-heading', TYPOGRAPHY.fontHeading, tokenVars['font-heading']);
check('font-size-xs', TYPOGRAPHY.sizes.xs, typoVars['font-size-xs']);
check('font-size-sm', TYPOGRAPHY.sizes.sm, typoVars['font-size-sm']);
check('font-size-base', TYPOGRAPHY.sizes.base, typoVars['font-size-base']);
check('font-size-lg', TYPOGRAPHY.sizes.lg, typoVars['font-size-lg']);
check('font-size-xl', TYPOGRAPHY.sizes.xl, typoVars['font-size-xl']);
check('font-size-xxl', TYPOGRAPHY.sizes.xxl, typoVars['font-size-xxl']);

if (failures.length) {
  console.error('토큰 드리프트 발견 — design-tokens.js 와 web CSS 값이 다르다:');
  for (const f of failures) console.error('  -', f);
  process.exit(1);
}

const total = Object.keys(colorVars).length + Object.keys(tokenVars).length + Object.keys(typoVars).length;
console.log(`토큰 정합성 OK (CSS 변수 ${total}개 스캔, design-tokens.js 기준 일치)`);
