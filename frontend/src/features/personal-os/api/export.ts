import { apiClient } from '@/api/client'

/** 下载个人 AI OS Markdown ZIP 导出包 */
export async function downloadOsExport(): Promise<void> {
  const { data } = await apiClient.get<Blob>('/os/export', {
    responseType: 'blob',
  })
  const stamp = new Date().toISOString().slice(0, 10)
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = `personal-ai-os-${stamp}.zip`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
