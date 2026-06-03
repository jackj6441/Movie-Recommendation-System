import { useState } from "react"

export function MovieThumb({ url }: { url: string }) {
  const [hidden, setHidden] = useState(false)
  if (hidden) return null
  return (
    <img
      className="movie-thumb"
      src={url}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setHidden(true)}
    />
  )
}
