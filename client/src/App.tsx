import { useRef, useState, useCallback } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import { PipecatClientProvider } from "@pipecat-ai/client-react";
import { motion, AnimatePresence } from "framer-motion";
import { IntakeForm } from "./IntakeForm";
import { VoicePanel } from "./VoicePanel";
import { OnboardingExperience } from "./OnboardingExperience";
import "./index.css";

export default function App() {
  const [onboardingDone, setOnboardingDone] = useState(false);

  const clientRef = useRef(
    new PipecatClient({
      transport: new SmallWebRTCTransport({
        // connectionUrl is the deprecated but simpler option — works for local dev
        connectionUrl: "http://localhost:7860",
      }),
    })
  );

  const handleOnboardingComplete = useCallback(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
    setOnboardingDone(true);
  }, []);

  return (
    // Cast needed: client-react bundles its own PipecatClient type declaration
    // under the bare "client-js" specifier; at runtime these are identical.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    <PipecatClientProvider client={clientRef.current as any}>
      <AnimatePresence mode="wait">
        {!onboardingDone ? (
          <motion.div
            key="onboarding"
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
          >
            <OnboardingExperience onComplete={handleOnboardingComplete} />
          </motion.div>
        ) : (
          <motion.div
            key="main"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <div className="min-h-screen bg-gray-100 py-8 px-4">
              <VoicePanel />
              <IntakeForm />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </PipecatClientProvider>
  );
}
