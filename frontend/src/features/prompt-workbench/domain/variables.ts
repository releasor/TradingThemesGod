const VAR_RE = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g

/** 提取 Prompt 中的 {{variable}} 名称，去重并保持出现顺序 */
export function extractVariables(body: string): string[] {
  const seen = new Set<string>()
  const names: string[] = []
  for (const match of body.matchAll(VAR_RE)) {
    const name = match[1]
    if (!seen.has(name)) {
      seen.add(name)
      names.push(name)
    }
  }
  return names
}

export function fillVariables(
  body: string,
  values: Record<string, string>
): string {
  return body.replace(VAR_RE, (_full, name: string) => {
    const value = values[name]
    return value !== undefined ? value : `{{${name}}}`
  })
}
