import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],

      // JSX 에서 참조되는 컴포넌트(PascalCase)/상수(UPPER_SNAKE)는 사용으로 간주.
      // (eslint-plugin-react 없이 JSX 사용 인식 — Vite 표준 flat config 방식)
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],

      // 컴포넌트에서 fetch 직접 호출 금지 (services/api의 BaseApiClient만 허용)
      'no-restricted-globals': [
        'error',
        {
          name: 'fetch',
          message: 'services/api의 BaseApiClient를 통해서만 호출하세요',
        },
      ],

      // console.log 금지 — utils/logger 사용
      'no-console': ['error', { allow: ['warn', 'error'] }],

      'no-restricted-syntax': [
        'error',
        {
          selector:
            "BinaryExpression[left.property.name=/_cd$|^status$/][right.type='Literal']",
          message: '@shotpocket/shared categories 상수를 사용하세요',
        },
        {
          selector:
            "JSXAttribute[name.name='style'] Property[key.name=/color|background/i][value.type='Literal']",
          message: 'CSS 변수 토큰을 사용하세요',
        },
      ],
    },
  },
  {
    // 유일하게 fetch 를 직접 사용할 수 있는 계층
    files: ['**/src/services/api/**'],
    rules: {
      'no-restricted-globals': 'off',
    },
  },
];
