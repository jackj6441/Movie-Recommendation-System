import { useEffect, useRef } from "react"
import * as d3 from "d3"
import type { ExplainResponse } from "../../types"
import { formatTitle } from "../../utils/format"

export function ScoreBreakdown({ explain }: { explain: ExplainResponse | null }) {
  const chartRef = useRef<SVGSVGElement | null>(null)

  useEffect(() => {
    if (!explain || !chartRef.current) return
    const items = explain.topk
    if (!items.length) return

    const contentAvailable = explain.content_available
    const stackedItems = items.map((item) => ({
      ...item,
      content: contentAvailable ? item.content : 0,
    }))

    const width = 720
    const rowHeight = 28
    const labelWidth = 240
    const valueWidth = 64
    const barWidth = width - labelWidth - valueWidth - 24
    const height = items.length * rowHeight + 30

    const svg = d3.select(chartRef.current)
    svg.attr("width", width).attr("height", height)
    svg.selectAll("*").remove()
    svg.append("title").text("Hybrid score breakdown — green: collaborative filtering, orange: content signal")

    const maxFinal = d3.max(stackedItems, (d) => d.final) || 1
    const xScale = d3.scaleLinear().domain([0, maxFinal]).range([0, barWidth])

    const group = svg.append("g").attr("transform", "translate(0,10)")

    const row = group
      .selectAll("g")
      .data(stackedItems)
      .enter()
      .append("g")
      .attr("transform", (_, i) => `translate(0, ${i * rowHeight})`)

    row
      .append("text")
      .attr("x", 0)
      .attr("y", rowHeight - 10)
      .attr("font-size", "12px")
      .text((d) => {
        const t = formatTitle(d.title)
        return t.length > 34 ? `${t.slice(0, 34)}...` : t
      })

    row
      .append("rect")
      .attr("x", labelWidth)
      .attr("y", 6)
      .attr("height", 16)
      .attr("width", (d) => xScale(explain.alpha * d.ncf))
      .attr("fill", "#2f855a")

    row
      .append("rect")
      .attr("x", (d) => labelWidth + xScale(explain.alpha * d.ncf))
      .attr("y", 6)
      .attr("height", 16)
      .attr("width", (d) => xScale((1 - explain.alpha) * d.content))
      .attr("fill", "#c05621")

    row
      .append("text")
      .attr("x", labelWidth + barWidth + 10)
      .attr("y", rowHeight - 10)
      .attr("font-size", "12px")
      .text((d) => d.final.toFixed(3))
  }, [explain])

  if (!explain) return null

  return (
    <>
      <div className="chart-legend" aria-hidden="true">
        <span>
          <i style={{ background: "#2f855a" }} /> Collaborative
        </span>
        <span>
          <i style={{ background: "#c05621" }} /> Content
        </span>
      </div>
      <svg
        ref={chartRef}
        role="img"
        aria-label="Hybrid score breakdown: green bars show collaborative filtering contribution, orange bars show content signal contribution"
      />
      <div style={{ marginTop: "1.25rem" }}>
        <h3>Similar movies to your seeds</h3>
        <div className="list" style={{ marginTop: "0.75rem" }}>
          {explain.similar_movies.map((movie) => (
            <div className="row" key={movie.movie_id}>
              <span>{formatTitle(movie.title)}</span>
              <span className="score">{movie.similarity.toFixed(3)}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
