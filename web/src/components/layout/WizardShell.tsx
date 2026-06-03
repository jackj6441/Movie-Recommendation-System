import type { ReactNode } from "react"

type WizardShellProps = {
  rail: ReactNode
  children: ReactNode
}

/** Two-column wizard layout: persistent context rail + main step content. */
export function WizardShell({ rail, children }: WizardShellProps) {
  return (
    <div className="wizard-shell full-width">
      {rail}
      <div className="wizard-main">{children}</div>
    </div>
  )
}
