/** 模型名称模糊匹配：连续子串优先，其次子序列。 */
export function fuzzyScore(query: string, target: string): number {
  const q = query.trim().toLowerCase()
  const t = target.toLowerCase()
  if (!q) return 1
  if (t === q) return 1000
  if (t.startsWith(q)) return 500 + (q.length / Math.max(t.length, 1)) * 100
  const idx = t.indexOf(q)
  if (idx >= 0) return 200 + (q.length / Math.max(t.length, 1)) * 100 - idx * 0.1
  let ti = 0
  for (const ch of q) {
    ti = t.indexOf(ch, ti)
    if (ti < 0) return 0
    ti += 1
  }
  return 40 + (q.length / Math.max(t.length, 1)) * 40
}

export function filterModels(models: string[], query: string, limit = 80): string[] {
  const scored = models
    .map((name) => ({ name, score: fuzzyScore(query, name) }))
    .filter((item) => item.score > 0)
  scored.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name))
  return scored.slice(0, limit).map((item) => item.name)
}
