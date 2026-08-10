import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuthContext } from "../../lib/AuthContext";
import { askAgent, isBackendConfigured } from "../../lib/apiClient";
import type { MapPoint, ToolTraceEntry } from "../../types/agent";

interface Turn {
  question: string;
  answer: string;
  toolTrace: ToolTraceEntry[];
}

function formatArguments(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
    .join(", ");
}

/** A terminal-styled command console docked to the map — deliberately not a chat widget.
 * Questions are logged as "> question", tool calls as "▸ tool(args)" readout lines, and
 * results (nearest stops, geocoded points, reachable stops) get pinned on the map above
 * via onMapHighlight rather than rendered as a chat bubble. */
export default function DispatchConsole({
  feedId,
  onMapHighlight,
}: {
  feedId: string;
  onMapHighlight: (points: MapPoint[]) => void;
}) {
  const { isAuthenticated } = useAuthContext();
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [turns, busy]);

  if (!isBackendConfigured()) return null;

  async function submit() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const response = await askAgent({ feed_id: feedId, question, conversation_id: conversationId });
      setConversationId(response.conversation_id);
      setTurns((prev) => [...prev, { question, answer: response.answer, toolTrace: response.tool_trace }]);
      onMapHighlight(response.map_payload.points);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`dispatch${expanded ? " dispatch--open" : ""}`}>
      <button className="dispatch__handle" onClick={() => setExpanded((v) => !v)}>
        <span className="dispatch__prompt">DISPATCH</span>
        <span className="dispatch__hint">
          {expanded ? "▾ collapse" : "▸ ask about routes, stops, coverage…"}
        </span>
      </button>

      {expanded && (
        <div className="dispatch__body">
          {!isAuthenticated ? (
            <div className="dispatch__signin">
              Sign in to query this feed's live data. <Link to="/login">Sign in →</Link>
            </div>
          ) : (
            <>
              <div className="dispatch__log" ref={logRef}>
                {turns.length === 0 && !busy && (
                  <div className="dispatch__empty">
                    Try: "what stops are near downtown" or "how far can I get in 15 minutes from
                    Main St".
                  </div>
                )}
                {turns.map((turn, i) => (
                  <div className="dispatch__turn" key={i}>
                    <div className="dispatch__question">&gt; {turn.question}</div>
                    {turn.toolTrace.map((trace, j) => (
                      <div className="dispatch__trace" key={j}>
                        ▸ {trace.tool_name}({formatArguments(trace.arguments)})
                      </div>
                    ))}
                    <div className="dispatch__answer">{turn.answer}</div>
                  </div>
                ))}
                {busy && <div className="dispatch__trace dispatch__trace--pending">▸ working…</div>}
              </div>
              {error && <div className="dispatch__error">{error}</div>}
              <div className="dispatch__input-row">
                <span className="dispatch__caret">›</span>
                <input
                  className="dispatch__input"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") submit();
                  }}
                  placeholder="ask about routes, stops, coverage…"
                  disabled={busy}
                  autoFocus
                />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
