// 색상·z-index·폰트 하드코딩 차단. 토큰 정의부(components/theme/)만 예외.
export default {
  rules: {
    'color-no-hex': true,
    'declaration-property-value-disallowed-list': {
      color: [/^rgb/, /^hsl/, /^#/],
      'background-color': [/^rgb/, /^hsl/, /^#/],
      'border-color': [/^rgb/, /^hsl/, /^#/],
    },
    'declaration-property-value-allowed-list': {
      'z-index': [/^var\(--z-/],
      'font-family': [/^var\(--font-/],
    },
  },
  ignoreFiles: ['**/components/theme/**', '**/dist/**', '**/node_modules/**'],
};
