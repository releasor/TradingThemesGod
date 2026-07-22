import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default [
  // 全局忽略目录
  {
    ignores: ['node_modules/**', 'dist/**', 'coverage/**'],
  },
  // ESLint 推荐规则
  js.configs.recommended,
  // TypeScript 推荐规则（flat config 数组，包含 parser 和 eslint-recommended）
  ...tseslint.configs['flat/recommended'],
  // 全局语言选项
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
  },
  // React Hooks 规则（flat config）
  reactHooks.configs['recommended-latest'],
  // React Refresh 规则（flat config）
  reactRefresh.configs.recommended,
  // 自定义规则
  {
    rules: {
      'react-refresh/only-export-components': [
        'warn',
        {
          allowConstantExport: true,
          allowExportNames: ['useToastContext', 'useTheme', 'useToast', 'getVisiblePages'],
        },
      ],
    },
  },
  // 测试文件特殊规则
  {
    files: ['**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}'],
    rules: {
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
];
