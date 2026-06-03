import type { ReactNode } from "react"
import { StepProgress } from "./StepProgress"
import { TmdbFooter } from "./TmdbFooter"

type View = "recommender" | "evidence"

type AppShellProps = {
  view: View
  step: number
  onViewChange: (view: View) => void
  headerAlerts?: ReactNode
  children: ReactNode
}

export function AppShell({ view, step, onViewChange, headerAlerts, children }: AppShellProps) {
  return (
    <main className="page">
      <section className="header">
        <h1 className="title">Movie Recommender</h1>
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
        {view === "recommender" && <StepProgress currentStep={step} />}
        {headerAlerts}
      </section>
      {children}
      <TmdbFooter />
    </main>
  )
}
