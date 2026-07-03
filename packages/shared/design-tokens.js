// ShotPocket design tokens (JS source of truth).
// 다크 퍼스트 팔레트. CSS 토큰(web/src/components/theme/)과 값이 일치해야 한다.

export const COLORS = {
  // Gray scale (900 = 가장 어두움, 50 = 가장 밝음)
  gray900: '#0B0B0F',
  gray800: '#141419',
  gray700: '#1E1E26',
  gray600: '#2A2A34',
  gray500: '#3A3A46',
  gray400: '#565663',
  gray300: '#7C7C8A',
  gray200: '#A8A8B3',
  gray100: '#D4D4DC',
  gray50: '#F4F4F7',

  // Brand
  brandPrimary: '#7C5CFF',
  brandPrimaryStrong: '#6344E6',
  brandPrimarySoft: '#9E86FF',
  accent: '#C8FF3D',
  accentStrong: '#B2E82A',

  // Semantic
  surfaceBase: '#0B0B0F',
  surfaceRaised: '#141419',
  textPrimary: '#F4F4F7',
  textMuted: '#A8A8B3',
  borderSoft: '#2A2A34',
  danger: '#FF5C6C',
  success: '#3DDC97',
};

// 4px 배수 스케일
export const SPACING = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  7: '28px',
  8: '32px',
};

export const RADIUS = {
  sm: '6px',
  base: '10px',
  lg: '16px',
  full: '9999px',
};

export const SHADOW = {
  base: '0 1px 2px rgba(0, 0, 0, 0.4)',
  raised: '0 8px 24px rgba(0, 0, 0, 0.5)',
};

export const TYPOGRAPHY = {
  fontBody:
    "'Pretendard', system-ui, -apple-system, 'Segoe UI', Roboto, 'Apple SD Gothic Neo', sans-serif",
  fontHeading:
    "'Pretendard', system-ui, -apple-system, 'Segoe UI', Roboto, 'Apple SD Gothic Neo', sans-serif",
  sizes: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '22px',
    xxl: '28px',
  },
};

export const Z_INDEX = {
  nav: 100,
  overlay: 200,
  modal: 300,
  toast: 400,
};
