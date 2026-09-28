export const OPTIMIZE_FRAMEWORKS = [
  {
    id: 'CRISPE',
    label: 'CRISPE',
    hint: '角色、背景、任务、格式与示例',
    description:
      '适合需要明确角色、背景、任务目标、输出格式与示例的完整型 Prompt，结构最齐全。',
  },
  {
    id: 'CO-STAR',
    label: 'CO-STAR',
    hint: '精确控制风格与受众',
    description:
      '适合对外沟通、文案与内容生成：强调上下文、目标、风格、语气、受众与响应格式。',
  },
  {
    id: 'APE',
    label: 'APE',
    hint: '短任务、直接',
    description: '适合短平快任务：动作（Action）、目的（Purpose）、期望（Expectation）三件套。',
  },
  {
    id: 'BROKE',
    label: 'BROKE',
    hint: '复杂任务与可衡量结果',
    description:
      '适合复杂、多步骤工作流：背景、角色、目标、关键结果与可执行步骤写清楚。',
  },
  {
    id: 'TRACE',
    label: 'TRACE',
    hint: '用示例带动结构',
    description: '适合需要示例驱动的任务：任务、角色、动作、上下文与示例一起约束输出。',
  },
  {
    id: 'RTF',
    label: 'RTF',
    hint: '简短角色、任务、格式',
    description: '适合极简约束：角色（Role）、任务（Task）、格式（Format）三行说清即可。',
  },
] as const

export type FrameworkId = (typeof OPTIMIZE_FRAMEWORKS)[number]['id']

export function getFrameworkMeta(id: string) {
  return OPTIMIZE_FRAMEWORKS.find((f) => f.id === id) ?? null
}

export const EXTRA_GOAL_CHIPS = [
  { id: 'shorter', label: '更短', value: '更短、更精炼，去掉冗余' },
  { id: 'formal', label: '更正式', value: '语气更正式、专业' },
  { id: 'vars', label: '可含变量', value: '保留并规范 {{变量}} 占位，便于复用' },
  { id: 'json', label: '输出 JSON', value: '明确要求结构化 JSON 输出，并给出字段说明' },
  { id: 'steps', label: '分步骤', value: '要求分步骤执行，步骤清晰可检查' },
] as const

export const OPTIMIZE_SAMPLES = [
  {
    title: '研报摘要助手',
    body: '你是一名卖方分析师助理。请用中文总结用户给出的研报要点，输出：核心结论、关键数据、风险点。语气客观，不超过 300 字。',
  },
  {
    title: '题材催化提炼',
    body: '根据输入的新闻或公告，提炼可能影响 A 股题材的催化信息。输出格式：题材名称、催化类型、时间敏感度、一句话逻辑。不要编造数据。',
  },
] as const
