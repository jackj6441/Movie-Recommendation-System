import type { SystemEvidence } from "../../types"
import { formatLatency, formatMetric } from "../../utils/format"

type EvidenceDashboardProps = {
  evidence: SystemEvidence | null
  loading: boolean
  error: string | null
  onRetry: () => void
}

export function EvidenceDashboard({ evidence, loading, error, onRetry }: EvidenceDashboardProps) {
  const maxRecall = Math.max(
    evidence?.evaluation.recall_at_k ?? 0,
    evidence?.evaluation.popularity_baseline_recall_at_k ?? 0,
    0.01
  )
  const recallLift = evidence ? formatLift(evidence.evaluation.recall_at_k, evidence.evaluation.popularity_baseline_recall_at_k) : null
  const servingReady = evidence
    ? evidence.serving.status === "ok" &&
      evidence.serving.content_ok &&
      evidence.serving.catalog_ok
    : false

  return (
    <section className="layout evidence-layout">
      <div className="card full-width">
        <h2>System Evidence</h2>
        <div className="subtitle">
          Three checks for reviewers: serving readiness, model quality, and deployment proof.
        </div>
        {loading && (
          <div aria-busy="true" aria-label="Loading system evidence">
            <div className="skeleton skeleton-text" style={{ width: "40%" }} />
            <div className="skeleton skeleton-text" style={{ width: "60%" }} />
          </div>
        )}
        {error && (
          <div role="alert">
            <p className="error-text">System evidence unavailable. Check the API and try again.</p>
            <button type="button" className="retry-btn" onClick={onRetry}>
              Retry
            </button>
          </div>
        )}
        {evidence && (
          <>
            <div className="evidence-proof-grid" aria-label="System proof summary">
              <article className="evidence-proof">
                <span>Serving is live</span>
                <strong>{servingReady ? "Ready" : "Degraded"}</strong>
                <p>
                  API health, content embeddings, and catalog artifacts are checked before this demo
                  claims recommendations are ready.
                </p>
              </article>
              <article className="evidence-proof">
                <span>Model beats baseline</span>
                <strong>{recallLift ?? "n/a"}</strong>
                <p>
                  Current Recall@K is compared with a popularity baseline so quality is anchored
                  to a simple alternative.
                </p>
              </article>
              <article className="evidence-proof">
                <span>Deployment is reproducible</span>
                <strong>{evidence.deployment.platform}</strong>
                <p>
                  The running demo uses {evidence.deployment.runtime}, matching the portfolio
                  deployment story rather than a local-only mock.
                </p>
              </article>
            </div>
            <div className="evidence-summary">
              <span className="evidence-pill">System: {evidence.system_name}</span>
              <span className="evidence-pill">Model version: {evidence.serving.model_version}</span>
              <span className="evidence-pill">RAG: {evidence.rag.public_provider}</span>
            </div>
          </>
        )}
      </div>

      {evidence && (
        <>
          <div className="card evidence-card">
            <h2>Serving Health</h2>
            <div className="subtitle">
              A reviewer can trust the demo only when the online dependencies are present.
            </div>
            <div className="metric-grid">
              <div>
                <span>Status</span>
                <strong>{evidence.serving.status}</strong>
              </div>
              <div>
                <span>Content</span>
                <strong>{evidence.serving.content_ok ? "ok" : "missing"}</strong>
              </div>
              <div>
                <span>Catalog</span>
                <strong>{evidence.serving.catalog_ok ? "ok" : "missing"}</strong>
              </div>
            </div>
          </div>

          <div className="card evidence-card">
            <h2>Evaluation Quality</h2>
            <div className="subtitle">
              Offline metrics show whether the recommender ranks relevant movies and covers the catalog.
            </div>
            <div className="metric-grid">
              <div>
                <span>Ranking quality</span>
                <strong>{formatMetric(evidence.evaluation.ndcg_at_k)}</strong>
                <small>NDCG@K, higher is better</small>
              </div>
              <div>
                <span>Coverage</span>
                <strong>{formatMetric(evidence.evaluation.recommendation_coverage)}</strong>
                <small>Catalog reach</small>
              </div>
              <div>
                <span>Diversity</span>
                <strong>{formatMetric(evidence.evaluation.topk_diversity)}</strong>
                <small>Variety across top picks</small>
              </div>
            </div>
          </div>

          <div className="card evidence-card">
            <h2>Current vs Popularity Baseline</h2>
            <div className="subtitle">
              Current ranking is {recallLift} the popularity baseline on Recall@K.
            </div>
            <div className="baseline-bars" aria-label="Recall@K baseline comparison">
              <div className="baseline-row">
                <span>Current Recall@K</span>
                <div className="baseline-track">
                  <div
                    className="baseline-fill current"
                    style={{ width: `${(evidence.evaluation.recall_at_k / maxRecall) * 100}%` }}
                  />
                </div>
                <strong>{formatMetric(evidence.evaluation.recall_at_k)}</strong>
              </div>
              <div className="baseline-row">
                <span>Popularity Baseline Recall@K</span>
                <div className="baseline-track">
                  <div
                    className="baseline-fill baseline"
                    style={{
                      width: `${(evidence.evaluation.popularity_baseline_recall_at_k / maxRecall) * 100}%`,
                    }}
                  />
                </div>
                <strong>{formatMetric(evidence.evaluation.popularity_baseline_recall_at_k)}</strong>
              </div>
            </div>
            <details className="evidence-details">
              <summary>Model artifact details</summary>
              <p className="subtle">{evidence.model_truth.product_ranking_path}</p>
              {evidence.model_truth.roadmap && (
                <p className="subtle">{evidence.model_truth.roadmap}</p>
              )}
            </details>
          </div>

          <div className="card evidence-card">
            <h2>Latency Benchmark</h2>
            <div className="subtitle">Committed benchmark artifact p95 latency.</div>
            <div className="metric-grid">
              <div>
                <span>Recommendations p95</span>
                <strong>{formatLatency(evidence.benchmark.recommendations_p95_ms)}</strong>
              </div>
              <div>
                <span>RAG explanations p95</span>
                <strong>{formatLatency(evidence.benchmark.rag_explanations_p95_ms)}</strong>
              </div>
            </div>
          </div>

          <div className="card evidence-card">
            <h2>RAG & Safety</h2>
            <div className="subtitle">Public demo provider and secret handling policy.</div>
            <div className="metric-grid">
              <div>
                <span>Provider</span>
                <strong>{evidence.rag.public_provider}</strong>
              </div>
            </div>
            <p className="subtle">{evidence.rag.secret_policy}</p>
          </div>

          <div className="card evidence-card">
            <h2>AWS EC2 Deployment</h2>
            <div className="subtitle">Live deployment target for portfolio review.</div>
            <div className="metric-grid">
              <div>
                <span>Platform</span>
                <strong>{evidence.deployment.platform}</strong>
              </div>
              <div>
                <span>Runtime</span>
                <strong>{evidence.deployment.runtime}</strong>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  )
}

function formatLift(current: number, baseline: number) {
  if (baseline <= 0) return "baseline unavailable"
  return `${(current / baseline).toFixed(1)}x Recall@K`
}
