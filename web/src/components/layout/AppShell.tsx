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
      <section className="header">
        <div className="app-topbar">
          <h1 className="title">
            <span className="brand-mark" aria-hidden="true">M</span>
            Movie Recommender
          </h1>
          <div className="view-tabs" role="group" aria-label="Primary views">
            <button
              type="button"
              className={`view-tab ${view === "recommender" ? "active" : ""}`}
              onClick={() => onViewChange("recommender")}
            >
              Recommender
            </button>
            <button
              type="button"
              className={`view-tab ${view === "evidence" ? "active" : ""}`}
              onClick={() => onViewChange("evidence")}
            >
              System Evidence
            </button>
          </div>
        </div>
        {headerAlerts}
      </section>
      {children}
      <TmdbFooter />
    </main>
  )
}
