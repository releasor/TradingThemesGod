/** 工信部 ICP 备案号，需出现在网站首页底部并链到备案系统 */
export function IcpBeian() {
  return (
    <footer className="flex shrink-0 justify-center px-4 py-2 text-center">
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        data-testid="icp-beian-link"
      >
        闽ICP备2026020085号-1
      </a>
    </footer>
  )
}
