export const OPTIMIZE_FRAMEWORKS = [
  {
    id: 'CRISPE',
    label: 'CRISPE',
    hint: '角色、背景、任务、个性与示例',
    description:
      '按 Capacity/Role、Insight、Statement、Personality、Experiment 组织，适合需要明确角色与约束的完整 Prompt。',
  },
  {
    id: 'CO-STAR',
    label: 'CO-STAR',
    hint: '情境、目标、风格、语气、受众、格式',
    description:
      '按 Context、Objective、Style、Tone、Audience、Response 组织，适合对外沟通与文案类生成。',
  },
  {
    id: 'APE',
    label: 'APE',
    hint: '行动、目的、期望',
    description: '按 Action、Purpose、Expectation 组织，适合短平快任务，结构直给。',
  },
  {
    id: 'BROKE',
    label: 'BROKE',
    hint: '背景、角色、目标、结果、演化',
    description:
      '按 Background、Role、Objectives、Key results、Evolve 组织，适合复杂、多步骤工作流。',
  },
  {
    id: 'TRACE',
    label: 'TRACE',
    hint: '任务、请求、动作、上下文、示例',
    description: '按 Task、Request、Action、Context、Example 组织，适合需要示例驱动的结构化任务。',
  },
  {
    id: 'RTF',
    label: 'RTF',
    hint: '角色、任务、格式',
    description: '按 Role、Task、Format 组织，适合极简约束、说明即用的场景。',
  },
] as const

export type FrameworkId = (typeof OPTIMIZE_FRAMEWORKS)[number]['id']

export function getFrameworkMeta(id: string) {
  return OPTIMIZE_FRAMEWORKS.find((f) => f.id === id) ?? null
}

export const EXTRA_GOAL_CHIPS = [
  { id: 'shorter', label: '更短', value: '更短、更精炼，去掉废话' },
  { id: 'formal', label: '更正式', value: '语气更正式、专业' },
  { id: 'vars', label: '可含变量', value: '保留或补充规范 {{变量}} 占位符便于复用' },
  { id: 'json', label: '输出 JSON', value: '明确要求结构化 JSON 输出并给出字段说明' },
  { id: 'steps', label: '分步骤', value: '要求分步骤执行，步骤清晰可检查' },
] as const

export const ITERATE_CHIPS = [
  { id: 'shorter', label: '更短', value: '在保留要点的前提下明显缩短' },
  { id: 'formal', label: '更正式', value: '语气更正式、专业' },
  { id: 'vars', label: '补变量', value: '为可变部分补充 {{变量}} 占位符' },
  { id: 'json', label: '改 JSON', value: '改为明确的结构化 JSON 输出要求' },
  { id: 'steps', label: '更分步', value: '拆成更清晰的分步执行说明' },
] as const

export const OPTIMIZE_SAMPLES = [
  {
    title: '研报摘要助手',
    body: '你是一名卖方分析师助理。请用中文总结用户给出的研报要点，输出：核心结论、关键数据、风险点。语气客观，不超过 300 字。',
  },
  {
    title: '题材催化提炼',
    body: '根据新闻标题或公告，提炼可能影响 A 股题材的催化信息。输出格式：题材名称、催化类型、时效判断、一句话逻辑、需要核实的点。',
  },
] as const
