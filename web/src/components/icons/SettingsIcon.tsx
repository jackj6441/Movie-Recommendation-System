import type { IconProps } from "./types"

export function SettingsIcon({ className, size = 24, "aria-hidden": ariaHidden = true }: IconProps) {
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
      <circle cx="12" cy="12" r="2.75" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.5 5.5l1.55 1.55M16.95 16.95l1.55 1.55M5.5 18.5l1.55-1.55M16.95 7.05l1.55-1.55"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  )
}
