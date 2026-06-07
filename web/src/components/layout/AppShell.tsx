import type { ReactNode } from "react"
import { TmdbFooter } from "./TmdbFooter"

type View = "recommender" | "evidence"

type AppShellProps = {
  view: View
  onViewChange: (view: View) => void
  headerAlerts?: ReactNode
  children: ReactNode
}

export function AppShell({ view, onViewChange, headerAlerts, children }: AppShellProps) {
  return (
    <main className="page">
      <header className="header app-header">
        <div className="app-topbar">
          <p className="app-brand">Movie Recommender</p>
          <nav className="view-segment" role="tablist" aria-label="Primary views">
            <button
              type="button"
              role="tab"
              aria-selected={view === "recommender"}
              className={`view-segment-btn${view === "recommender" ? " is-active" : ""}`}
              onClick={() => onViewChange("recommender")}
            >
              Recommender
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={view === "evidence"}
              className={`view-segment-btn${view === "evidence" ? " is-active" : ""}`}
              onClick={() => onViewChange("evidence")}
            >
              System Evidence
            </button>
          </nav>
        </div>
        {headerAlerts}
      </header>
      {children}
      <TmdbFooter />
    </main>
  )
}
