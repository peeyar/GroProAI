import { useEffect, useRef, useState } from 'react'
import { sendChat } from '../api'
import type { ChartSpec, ChatMessage } from '../types'
import MiniBar from './MiniBar'
import Waterfall from './Waterfall'

interface Props {
  onPin: (chart: ChartSpec) => void
}

const SUGGESTIONS = [
  'Why did revenue change?',
  'How did FX move?',
  'Top customers?',
  'What about HVOR?',
  'Compare to last quarter',
]

const WELCOME: ChatMessage = {
  role: 'assistant',
  text:
    'Ask me about the quarter — why revenue moved, FX, customers, or a business unit. ' +
    'Demo mode: answers are canned; the real AI chat lands in Phase 3.',
}

function ChartBubble({ chart, onPin }: { chart: ChartSpec; onPin: (c: ChartSpec) => void }) {
  return (
    <div className="chat-chart">
      <div className="chat-chart-title">{chart.title}</div>
      {chart.chartType === 'waterfall' ? (
        <Waterfall
          compact
          buckets={chart.data.map((d) => ({ key: d.name, label: d.name, value: d.value }))}
          total={{
            key: 'total',
            label: 'Total',
            value: chart.total ?? chart.data.reduce((s, d) => s + d.value, 0),
          }}
        />
      ) : (
        <MiniBar data={chart.data} />
      )}
      <button className="ghost-btn small" onClick={() => onPin(chart)}>
        📌 Pin to My View
      </button>
    </div>
  )
}

export default function ChatPanel({ onPin }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: message }])
    setBusy(true)
    try {
      const res = await sendChat(message)
      setMessages((m) => [...m, { role: 'assistant', text: res.reply, chart: res.chart }])
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: "I can't reach the demo backend — is uvicorn running on port 8000?",
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card chat">
      <div className="chat-head">
        <h2 className="card-title">Ask GroPro</h2>
        <span
          className="demo-chip"
          title="Canned answers from demo rules — real natural-language chat arrives in Phase 3."
        >
          Demo
        </span>
      </div>

      <div className="chat-msgs" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <p>{m.text}</p>
            {m.chart && <ChartBubble chart={m.chart} onPin={onPin} />}
          </div>
        ))}
        {busy && <div className="msg assistant thinking">…</div>}
      </div>

      <div className="chips">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="chip" onClick={() => send(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>

      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask why revenue changed…"
          aria-label="Chat message"
        />
        <button type="submit" className="send-btn" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
