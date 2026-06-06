import { useCallback, useEffect, useId, useRef, useState } from "react"
import {
  YEAR_TRACK_MAX,
  YEAR_TRACK_MIN,
  formatYearRangeLabel,
} from "../../lib/tasteYear"

type YearRangeSliderProps = {
  min: number
  max: number
  disabled?: boolean
  onChange: (min: number, max: number) => void
  onCommit: (min: number, max: number) => void
}

function clampYear(value: number): number {
  return Math.min(YEAR_TRACK_MAX, Math.max(YEAR_TRACK_MIN, value))
}

export function YearRangeSlider({
  min,
  max,
  disabled = false,
  onChange,
  onCommit,
}: YearRangeSliderProps) {
  const labelId = useId()
  const committingRef = useRef(false)
  const [dragging, setDragging] = useState(false)
  const liveMin = clampYear(min)
  const liveMax = clampYear(Math.max(min, max))
  const pendingRef = useRef({ min: liveMin, max: liveMax })

  useEffect(() => {
    pendingRef.current = { min: liveMin, max: liveMax }
  }, [liveMin, liveMax])

  const emitChange = useCallback(
    (nextMin: number, nextMax: number) => {
      const clampedMin = clampYear(nextMin)
      const clampedMax = clampYear(Math.max(clampedMin, nextMax))
      pendingRef.current = { min: clampedMin, max: clampedMax }
      onChange(clampedMin, clampedMax)
    },
    [onChange]
  )

  const handleMinChange = (value: number) => {
    emitChange(value, pendingRef.current.max)
  }

  const handleMaxChange = (value: number) => {
    emitChange(pendingRef.current.min, value)
  }

  const handlePointerUp = () => {
    if (disabled || !dragging) return
    setDragging(false)
    if (committingRef.current) return
    committingRef.current = true
    const { min: commitMin, max: commitMax } = pendingRef.current
    onCommit(commitMin, commitMax)
    window.setTimeout(() => {
      committingRef.current = false
    }, 0)
  }

  const minPercent =
    ((liveMin - YEAR_TRACK_MIN) / (YEAR_TRACK_MAX - YEAR_TRACK_MIN)) * 100
  const maxPercent =
    ((liveMax - YEAR_TRACK_MIN) / (YEAR_TRACK_MAX - YEAR_TRACK_MIN)) * 100

  return (
    <div
      className={`year-range-slider${disabled ? " year-range-slider--disabled" : ""}`}
      onMouseUp={handlePointerUp}
      onMouseLeave={dragging ? handlePointerUp : undefined}
      onTouchEnd={handlePointerUp}
    >
      <p id={labelId} className="year-range-slider-label">
        {formatYearRangeLabel(liveMin, liveMax >= YEAR_TRACK_MAX ? null : liveMax)}
      </p>
      <div className="year-range-slider-track-wrap">
        <div className="year-range-slider-track" aria-hidden="true">
          <div
            className="year-range-slider-range"
            style={{
              left: `${minPercent}%`,
              right: `${100 - maxPercent}%`,
            }}
          />
        </div>
        <input
          type="range"
          className="year-range-slider-thumb year-range-slider-thumb--min"
          min={YEAR_TRACK_MIN}
          max={YEAR_TRACK_MAX}
          value={liveMin}
          disabled={disabled}
          aria-label="Release year minimum"
          aria-labelledby={labelId}
          onChange={(event) => handleMinChange(Number(event.target.value))}
          onMouseDown={() => setDragging(true)}
          onTouchStart={() => setDragging(true)}
        />
        <input
          type="range"
          className="year-range-slider-thumb year-range-slider-thumb--max"
          min={YEAR_TRACK_MIN}
          max={YEAR_TRACK_MAX}
          value={liveMax}
          disabled={disabled}
          aria-label="Release year maximum"
          aria-labelledby={labelId}
          onChange={(event) => handleMaxChange(Number(event.target.value))}
          onMouseDown={() => setDragging(true)}
          onTouchStart={() => setDragging(true)}
        />
      </div>
    </div>
  )
}
