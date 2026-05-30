import { useEffect, useState } from "react";
import {
  useUISnapshot,
  useDefaultUICommandHandlers,
  usePipecatClient,
  PipecatClientAudio,
} from "@pipecat-ai/client-react";

// ── Dev test panel ─────────────────────────────────────────────────────────────
// Directly manipulates DOM to verify fields respond correctly — no bot needed.
// Hidden automatically in production builds.
function DevTestPanel() {
  const fillField = (id: string, value: string) => {
    const el = document.getElementById(id) as HTMLInputElement | HTMLTextAreaElement | null;
    if (!el) return;
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, "value"
    )?.set ?? Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
    nativeInputValueSetter?.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const highlightField = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add("ring-4", "ring-yellow-400");
    setTimeout(() => el.classList.remove("ring-4", "ring-yellow-400"), 1200);
    el.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <div className="mt-3 p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-xs">
      <div className="font-semibold text-yellow-800 mb-2">
        Dev — Test form fills (no bot needed)
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={() => fillField("patient-name", "Sarah Johnson")}
          className="px-2 py-1 bg-yellow-200 hover:bg-yellow-300 rounded transition-colors">
          Fill Name
        </button>
        <button onClick={() => fillField("date-of-birth", "1985-03-15")}
          className="px-2 py-1 bg-yellow-200 hover:bg-yellow-300 rounded transition-colors">
          Fill DOB
        </button>
        <button onClick={() => fillField("allergies", "Penicillin, sulfa drugs")}
          className="px-2 py-1 bg-yellow-200 hover:bg-yellow-300 rounded transition-colors">
          Fill Allergies
        </button>
        <button onClick={() => fillField("insurance-provider", "BlueCross BlueShield")}
          className="px-2 py-1 bg-yellow-200 hover:bg-yellow-300 rounded transition-colors">
          Fill Insurance
        </button>
        <button onClick={() => highlightField("patient-name")}
          className="px-2 py-1 bg-orange-200 hover:bg-orange-300 rounded transition-colors">
          Highlight Name
        </button>
        <button onClick={() => document.getElementById("emergency-name")?.scrollIntoView({ behavior: "smooth", block: "center" })}
          className="px-2 py-1 bg-orange-200 hover:bg-orange-300 rounded transition-colors">
          Scroll to Emergency
        </button>
      </div>
    </div>
  );
}

// ── Main voice panel ──────────────────────────────────────────────────────────
export function VoicePanel() {
  const client = usePipecatClient();
  const [status, setStatus] = useState<"idle" | "connecting" | "live">("idle");
  const [agentText, setAgentText] = useState("");
  const [userText, setUserText] = useState("");

  // Stream the form's accessibility tree to the bot when connected
  useUISnapshot({
    enabled: status === "live",
    debounceMs: 300,
    trackViewport: true,
  });

  // Install all six default UI command handlers:
  // set_input_value, highlight, click, scroll_to, focus, select_text
  useDefaultUICommandHandlers();

  const connect = async () => {
    if (!client) return;
    setStatus("connecting");
    try {
      await client.connect();
      setStatus("live");
    } catch (e) {
      console.error("Connection failed:", e);
      setStatus("idle");
    }
  };

  const disconnect = async () => {
    await client?.disconnect();
    setStatus("idle");
    setAgentText("");
    setUserText("");
  };

  useEffect(() => {
    if (!client) return;
    const onAgentText = (e: unknown) => {
      if (e && typeof e === "object" && "text" in e) setAgentText(String((e as { text: unknown }).text));
    };
    const onUserTranscript = (e: unknown) => {
      if (e && typeof e === "object" && "final" in e && "text" in e && (e as { final: unknown }).final) {
        setUserText(String((e as { text: unknown }).text));
      }
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const c = client as any;
    c.on("botTtsText", onAgentText);
    c.on("userTranscript", onUserTranscript);
    return () => {
      c.off("botTtsText", onAgentText);
      c.off("userTranscript", onUserTranscript);
    };
  }, [client]);

  return (
    <div className="max-w-2xl mx-auto mb-4 bg-white rounded-xl shadow-lg overflow-hidden">
      <div className="bg-blue-700 px-6 py-3 flex items-center justify-between">
        <span className="text-white font-semibold text-sm">ClearPath Voice Check-in</span>
        {status === "live" && (
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-green-300 text-xs">Live</span>
          </span>
        )}
      </div>

      <div className="p-4">
        {status === "idle" && (
          <button
            onClick={connect}
            className="w-full bg-blue-700 text-white py-3 rounded-lg font-semibold
                       hover:bg-blue-800 transition-colors"
          >
            Start Voice Check-in
          </button>
        )}

        {status === "connecting" && (
          <div className="text-center py-3 text-blue-500 text-sm animate-pulse">
            Connecting to ClearPath...
          </div>
        )}

        {status === "live" && (
          <div className="space-y-3">
            <div className="bg-gray-50 rounded-lg p-3 min-h-[60px] text-sm space-y-1">
              {agentText && (
                <p className="text-blue-700">
                  <span className="font-medium">Agent:</span> {agentText}
                </p>
              )}
              {userText && (
                <p className="text-gray-600">
                  <span className="font-medium">You:</span> {userText}
                </p>
              )}
              {!agentText && !userText && (
                <p className="text-gray-400 italic">Listening...</p>
              )}
            </div>
            <button
              onClick={disconnect}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              End session
            </button>
          </div>
        )}

        <PipecatClientAudio />

        {import.meta.env.DEV && <DevTestPanel />}
      </div>
    </div>
  );
}
