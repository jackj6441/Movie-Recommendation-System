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

  return (
    <section className="layout evidence-layout">
      <div className="card full-width">
        <h2>System Evidence</h2>
        <div className="subtitle">Current system vs baseline plus production readiness evidence.</div>
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
          <div className="evidence-summary">
            <span className="evidence-pill">System: {evidence.system_name}</span>
            <span className="evidence-pill">Model version: {evidence.serving.model_version}</span>
            <span className="evidence-pill">RAG: {evidence.rag.public_provider}</span>
          </div>
        )}
      </div>

      {evidence && (
        <>
          <div className="card evidence-card">
            <h2>Serving Health</h2>
            <div className="subtitle">Live readiness signal from the serving API.</div>
            <div className="metric-grid">
              <div>
                <span>Status</span>
                <strong>{evidence.serving.status}</strong>
              </div>
              <div>
                <span>Redis</span>
                <strong>{evidence.serving.redis_ok ? "ok" : "degraded"}</strong>
              </div>
              <div>
                <span>ONNX</span>
                <strong>{evidence.serving.onnx_ok ? "ok" : "missing"}</strong>
              </div>
              <div>
                <span>Metadata</span>
                <strong>{evidence.serving.metadata_ok ? "ok" : "missing"}</strong>
              </div>
            </div>
          </div>

          <div className="card evidence-card">
            <h2>Evaluation Quality</h2>
            <div className="subtitle">Offline quality and catalog behavior from the evaluation harness.</div>
            <div className="metric-grid">
              <div>
                <span>RMSE</span>
                <strong>{evidence.evaluation.rmse.toFixed(4)}</strong>
              </div>
              <div>
                <span>NDCG@K</span>
                <strong>{formatMetric(evidence.evaluation.ndcg_at_k)}</strong>
              </div>
              <div>
                <span>Coverage</span>
                <strong>{formatMetric(evidence.evaluation.recommendation_coverage)}</strong>
              </div>
              <div>
                <span>Diversity</span>
                <strong>{formatMetric(evidence.evaluation.topk_diversity)}</strong>
              </div>
            </div>
          </div>

          <div className="card evidence-card">
            <h2>Current vs Popularity Baseline</h2>
            <div className="subtitle">Baseline comparison, not a multi-model comparison.</div>
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
            <p className="subtle">{evidence.model_truth.product_ranking_path}</p>
            <p className="subtle">{evidence.model_truth.ncf_onnx_status}</p>
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
