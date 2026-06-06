// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useState } from "react"
import { YearRangeSlider } from "./YearRangeSlider"

function SliderHarness({
  onCommit,
}: {
  onCommit: (min: number, max: number) => void
}) {
  const [min, setMin] = useState(2000)
  const [max, setMax] = useState(2010)

  return (
    <YearRangeSlider
      min={min}
      max={max}
      onChange={(nextMin, nextMax) => {
        setMin(nextMin)
        setMax(nextMax)
      }}
      onCommit={onCommit}
    />
  )
}

describe("YearRangeSlider", () => {
  afterEach(() => {
    cleanup()
  })

  it("commits the latest dragged values on pointer release", () => {
    const onCommit = vi.fn()
    render(<SliderHarness onCommit={onCommit} />)

    const minThumb = screen.getByLabelText("Release year minimum")
    fireEvent.mouseDown(minThumb)
    fireEvent.change(minThumb, { target: { value: "1995" } })
    fireEvent.mouseUp(minThumb)

    expect(onCommit).toHaveBeenCalledWith(1995, 2010)
  })

  it("commits updated max thumb without waiting for parent re-render", () => {
    const onCommit = vi.fn()
    render(<SliderHarness onCommit={onCommit} />)

    const maxThumb = screen.getByLabelText("Release year maximum")
    fireEvent.mouseDown(maxThumb)
    fireEvent.change(maxThumb, { target: { value: "2019" } })
    fireEvent.mouseUp(maxThumb)

    expect(onCommit).toHaveBeenCalledWith(2000, 2019)
  })

  it("does not commit while disabled", () => {
    const onCommit = vi.fn()
    render(
      <YearRangeSlider
        min={2000}
        max={2010}
        disabled
        onChange={() => {}}
        onCommit={onCommit}
      />
    )

    const minThumb = screen.getByLabelText("Release year minimum")
    fireEvent.mouseDown(minThumb)
    fireEvent.mouseUp(minThumb)

    expect(onCommit).not.toHaveBeenCalled()
  })
})
