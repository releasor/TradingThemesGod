/** ExportButton 组件测试 */

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ExportButton } from "./ExportButton"

// 模拟 export 模块
vi.mock("@/lib/export", () => ({
  exportThemes: vi.fn(),
}))

import { exportThemes } from "@/lib/export"

describe("ExportButton", () => {
  const mockData = [
    {
      name: "人工智能",
      code: "AI001",
      heat_index: 95,
      rise_fall_pct: 3.5,
      stock_count: 50,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders export button", () => {
    render(<ExportButton data={mockData} />)
    expect(screen.getByText("导出")).toBeInTheDocument()
  })

  it("does not show dropdown initially", () => {
    render(<ExportButton data={mockData} />)
    expect(screen.queryByText("导出为 CSV")).not.toBeInTheDocument()
    expect(screen.queryByText("导出为 JSON")).not.toBeInTheDocument()
  })

  it("shows dropdown when button is clicked", () => {
    render(<ExportButton data={mockData} />)
    fireEvent.click(screen.getByText("导出"))
    expect(screen.getByText("导出为 CSV")).toBeInTheDocument()
    expect(screen.getByText("导出为 JSON")).toBeInTheDocument()
  })

  it("calls exportThemes with csv format when CSV option is clicked", () => {
    render(<ExportButton data={mockData} />)
    fireEvent.click(screen.getByText("导出"))
    fireEvent.click(screen.getByText("导出为 CSV"))
    expect(exportThemes).toHaveBeenCalledWith(mockData, "csv")
  })

  it("calls exportThemes with json format when JSON option is clicked", () => {
    render(<ExportButton data={mockData} />)
    fireEvent.click(screen.getByText("导出"))
    fireEvent.click(screen.getByText("导出为 JSON"))
    expect(exportThemes).toHaveBeenCalledWith(mockData, "json")
  })

  it("closes dropdown after export", () => {
    render(<ExportButton data={mockData} />)
    fireEvent.click(screen.getByText("导出"))
    fireEvent.click(screen.getByText("导出为 CSV"))
    expect(screen.queryByText("导出为 CSV")).not.toBeInTheDocument()
  })

  it("closes dropdown when backdrop is clicked", () => {
    render(<ExportButton data={mockData} />)
    fireEvent.click(screen.getByText("导出"))
    expect(screen.getByText("导出为 CSV")).toBeInTheDocument()
    // 点击背景遮罩
    const backdrop = document.querySelector(".fixed.inset-0")
    if (backdrop) {
      fireEvent.click(backdrop)
    }
    expect(screen.queryByText("导出为 CSV")).not.toBeInTheDocument()
  })

  it("applies custom className", () => {
    const { container } = render(
      <ExportButton data={mockData} className="my-class" />
    )
    expect(container.firstChild).toHaveClass("my-class")
  })

  it("toggles dropdown on repeated clicks", () => {
    render(<ExportButton data={mockData} />)
    const btn = screen.getByText("导出")
    // Open
    fireEvent.click(btn)
    expect(screen.getByText("导出为 CSV")).toBeInTheDocument()
    // Close
    fireEvent.click(btn)
    expect(screen.queryByText("导出为 CSV")).not.toBeInTheDocument()
  })
})