/** ImportButton 组件测试 */

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ImportButton } from "./ImportButton"

// 模拟 import 模块
vi.mock("@/lib/import", () => ({
  importFromFile: vi.fn(),
}))

import { importFromFile } from "@/lib/import"

describe("ImportButton", () => {
  const mockOnImport = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders import button", () => {
    render(<ImportButton onImport={mockOnImport} />)
    expect(screen.getByText("导入")).toBeInTheDocument()
  })

  it("does not show panel initially", () => {
    render(<ImportButton onImport={mockOnImport} />)
    expect(screen.queryByText("导入数据")).not.toBeInTheDocument()
  })

  it("shows panel when button is clicked", () => {
    render(<ImportButton onImport={mockOnImport} />)
    fireEvent.click(screen.getByText("导入"))
    expect(screen.getByText("导入数据")).toBeInTheDocument()
    expect(screen.getByText(/拖放文件到此处/)).toBeInTheDocument()
    expect(screen.getByText(/支持 CSV 和 JSON 格式/)).toBeInTheDocument()
  })

  it("shows file input with correct accept attribute", () => {
    render(<ImportButton onImport={mockOnImport} />)
    fireEvent.click(screen.getByText("导入"))
    const input = document.querySelector("input[type=file]")
    expect(input).toBeTruthy()
    expect(input).toHaveAttribute("accept", ".csv,.json")
  })

  it("shows format instructions", () => {
    render(<ImportButton onImport={mockOnImport} />)
    fireEvent.click(screen.getByText("导入"))
    expect(screen.getByText(/CSV: 需要包含表头行/)).toBeInTheDocument()
    expect(screen.getByText(/JSON: 数组格式/)).toBeInTheDocument()
  })

  it("shows success result after successful import", async () => {
    vi.mocked(importFromFile).mockResolvedValue({
      success: true,
      data: [{ name: "AI", code: "001" }],
      errors: [],
      total: 1,
      imported: 1,
    })

    render(
      <ImportButton
        onImport={mockOnImport}
      />
    )
    fireEvent.click(screen.getByText("导入"))

    // 模拟文件选择
    const file = new File(["name,code\nAI,001"], "test.csv", { type: "text/csv" })
    const input = document.querySelector("input[type=file]") as HTMLInputElement
    Object.defineProperty(input, "files", { value: [file] })
    fireEvent.change(input)

    // 等待异步操作
    await vi.waitFor(() => {
      expect(screen.getByText(/成功导入 1 条数据/)).toBeInTheDocument()
    })
    expect(mockOnImport).toHaveBeenCalledWith([{ name: "AI", code: "001" }])
  })

  it("shows error result after failed import", async () => {
    vi.mocked(importFromFile).mockResolvedValue({
      success: false,
      data: [],
      errors: ["解析失败"],
      total: 1,
      imported: 0,
    })

    render(<ImportButton onImport={mockOnImport} />)
    fireEvent.click(screen.getByText("导入"))

    const file = new File(["bad data"], "test.csv", { type: "text/csv" })
    const input = document.querySelector("input[type=file]") as HTMLInputElement
    Object.defineProperty(input, "files", { value: [file] })
    fireEvent.change(input)

    await vi.waitFor(() => {
      expect(screen.getByText("导入失败")).toBeInTheDocument()
    })
    expect(mockOnImport).not.toHaveBeenCalled()
  })

  it("closes panel when close button is clicked", () => {
    render(<ImportButton onImport={mockOnImport} />)
    fireEvent.click(screen.getByText("导入"))
    expect(screen.getByText("导入数据")).toBeInTheDocument()
    // 点击关闭按钮
    const closeBtn = document.querySelector("button .lucide-x")
    if (closeBtn) {
      fireEvent.click(closeBtn.closest("button")!)
    }
    expect(screen.queryByText("导入数据")).not.toBeInTheDocument()
  })

  it("applies custom className", () => {
    const { container } = render(
      <ImportButton onImport={mockOnImport} className="my-class" />
    )
    expect(container.firstChild).toHaveClass("my-class")
  })
})