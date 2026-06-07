import type { ReactNode } from "react"

export type PosterFrameVariant = "hero" | "strip"

type PosterFrameProps = {
  variant: PosterFrameVariant
  children: ReactNode
  className?: string
  interactive?: boolean
  disabled?: boolean
  title?: string
  ariaLabel?: string
  ariaPressed?: boolean
  onClick?: () => void
}

export function PosterFrame({
  variant,
  children,
  className = "",
  interactive = false,
  disabled = false,
  title,
  ariaLabel,
  ariaPressed,
  onClick,
}: PosterFrameProps) {
  const rootClass = [
    "poster-frame",
    `poster-frame--${variant}`,
    interactive ? "poster-frame--interactive" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ")

  const wood = (
    <span className="poster-frame__wood">
      <span className="poster-frame__mat">{children}</span>
    </span>
  )

  if (interactive) {
    return (
      <button
        type="button"
        className={rootClass}
        disabled={disabled}
        title={title}
        aria-label={ariaLabel}
        aria-pressed={ariaPressed}
        onClick={onClick}
      >
        {wood}
      </button>
    )
  }

  return (
    <div className={rootClass} aria-label={ariaLabel}>
      {wood}
    </div>
  )
}
