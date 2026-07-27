/** 全站键盘快捷键定义（面板与设置页共用） */

export interface KeyboardShortcutItem {
  key: string
  description: string
  modifiers?: string[]
}

export const KEYBOARD_SHORTCUTS: KeyboardShortcutItem[] = [
  { key: 'R', description: '刷新看板' },
  { key: 'T', description: '打开题材库' },
  { key: '/', description: '聚焦搜索' },
  { key: '?', description: '显示快捷键帮助' },
  { key: 'Esc', description: '关闭弹窗' },
]
