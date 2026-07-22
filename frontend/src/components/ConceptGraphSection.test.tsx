import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ConceptGraphSection } from './ConceptGraphSection'
import type { ConceptGraph } from '@/types/theme'

const graph: ConceptGraph = {
  node_count: 2, stock_count: 1, max_depth: 4, updated_at: null,
  roots: [{ id: 1, name: '机器人', node_type: 'domain', description: null, chain_level: null, market_logic: null, catalysts: [], risks: [], sources: [], confidence: 0.98, depth: 0, stocks: [], children: [
    { id: 2, name: '电子皮肤', node_type: 'technology', description: '柔性触觉阵列', chain_level: 'upstream', market_logic: null, catalysts: [], risks: [], sources: [], confidence: 0.88, depth: 4, children: [], stocks: [
      { code: '605488', name: '福莱新材', relation_type: '材料布局', rationale: '布局柔性传感器相关材料', relevance_score: 0.88, is_core: true, sources: [] },
    ] },
  ] }],
}

describe('ConceptGraphSection', () => {
  it('搜索深层节点时展示股票依据', async () => {
    render(<ConceptGraphSection graph={graph} />)
    await userEvent.type(screen.getByPlaceholderText('搜索细分、技术或股票'), '电子皮肤')
    expect(screen.getByText('电子皮肤')).toBeInTheDocument()
    expect(screen.getByText(/福莱新材/)).toBeInTheDocument()
    expect(screen.getByText(/柔性传感器/)).toBeInTheDocument()
  })

  it('空图谱不伪造节点', () => {
    render(<ConceptGraphSection graph={{ roots: [], node_count: 0, stock_count: 0, max_depth: 0, updated_at: null }} />)
    expect(screen.getByText('该题材尚无经过核验的细分图谱')).toBeInTheDocument()
  })
})
