import { useCallback, useState } from "react"
import { apiBase } from "./config"
import { AppShell } from "./components/layout/AppShell"
import { ChatRecommender } from "./components/chat/ChatRecommender"
import { EvidenceDashboard } from "./components/evidence/EvidenceDashboard"
import type { SystemEvidence } from "./types"

export default function App() {
  const [view, setView] = useState<"recommender" | "evidence">("recommender")
  const [systemEvidence, setSystemEvidence] = useState<SystemEvidence | null>(null)
  const [systemEvidenceLoading, setSystemEvidenceLoading] = useState(false)
  const [systemEvidenceError, setSystemEvidenceError] = useState<string | null>(null)

  const fetchSystemEvidence = useCallback(async () => {
    setSystemEvidenceLoading(true)
    setSystemEvidenceError(null)
    try {
      const res = await fetch(`${apiBase}/system/evidence`)
      if (!res.ok) {
        throw new Error(`Evidence failed: ${res.status}`)
      }
      const json = (await res.json()) as SystemEvidence
      setSystemEvidence(json)
    } catch (err) {
      setSystemEvidenceError(err instanceof Error ? err.message : "Unknown error")
      setSystemEvidence(null)
    } finally {
      setSystemEvidenceLoading(false)
    }
  }, [])

  const handleViewChange = (next: "recommender" | "evidence") => {
    setView(next)
    if (next === "evidence" && !systemEvidence && !systemEvidenceLoading) {
      fetchSystemEvidence()
    }
  }

  return (
    <AppShell view={view} onViewChange={handleViewChange}>
      {view === "evidence" ? (
        <EvidenceDashboard
          evidence={systemEvidence}
          loading={systemEvidenceLoading}
          error={systemEvidenceError}
          onRetry={fetchSystemEvidence}
        />
      ) : (
        <ChatRecommender />
      )}
    </AppShell>
  )
}
