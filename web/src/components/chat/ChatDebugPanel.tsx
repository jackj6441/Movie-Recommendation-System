import type { RagChatDebug } from "../../types"

type ChatDebugPanelProps = {
  debug: RagChatDebug
}

export function ChatDebugPanel({ debug }: ChatDebugPanelProps) {
  if (!import.meta.env.DEV) {
    return null
  }

  return (
    <details className="chat-debug-panel">
      <summary>Debug</summary>
      <pre className="chat-debug-panel-body">{JSON.stringify(debug, null, 2)}</pre>
    </details>
  )
}
