/** 图表颜色工具函数
 *
 * 提供图表颜色方案和暗色模式支持。
 */

/** 图表颜色调色板 */
export const CHART_COLOR_PALETTE = [
  '#5470c6', // 蓝
  '#91cc75', // 绿
  '#fac858', // 黄
  '#ee6666', // 红
  '#73c0de', // 浅蓝
  '#3ba272', // 深绿
  '#fc8452', // 橙
  '#9a60b4', // 紫
  '#ea7ccc', // 粉
  '#48b8d0', // 青
]

/** 涨跌颜色（中国股市惯例：红涨绿跌） */
export const RISE_FALL_COLORS = {
  rise: '#ef4444',    // 红色 - 上涨
  fall: '#22c55e',    // 绿色 - 下跌
  neutral: '#9ca3af', // 灰色 - 持平
}

/** 产业链层级颜色 */
export const CHAIN_LEVEL_COLORS = {
  upstream: '#5470c6',   // 蓝色 - 上游
  midstream: '#91cc75',  // 绿色 - 中游
  downstream: '#fac858', // 黄色 - 下游
}

/** 获取图表主题颜色
 *
 * 根据当前是否为暗色模式返回相应的颜色配置。
 */
export function getChartThemeColors(isDark: boolean) {
  return {
    // 文本颜色
    textColor: isDark ? '#e5e7eb' : '#374151',
    // 次要文本颜色
    secondaryTextColor: isDark ? '#9ca3af' : '#6b7280',
    // 网格线颜色
    gridBorderColor: isDark ? '#374151' : '#e5e7eb',
    // 背景颜色（透明以继承页面背景）
    backgroundColor: 'transparent',
    // 工具提示背景
    tooltipBg: isDark ? '#1f2937' : '#ffffff',
    // 工具提示文本
    tooltipTextColor: isDark ? '#e5e7eb' : '#374151',
    // 工具提示边框
    tooltipBorderColor: isDark ? '#4b5563' : '#e5e7eb',
  }
}
