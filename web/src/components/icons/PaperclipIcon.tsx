import type { IconProps } from "./types"

export function PaperclipIcon({ className, size = 24, "aria-hidden": ariaHidden = true }: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden={ariaHidden}
    >
      <path
        d="M8.5 13.5 14.2 7.8a3 3 0 1 1 4.2 4.2l-6.8 6.8a4.5 4.5 0 0 1-6.4-6.4l7.2-7.2"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
