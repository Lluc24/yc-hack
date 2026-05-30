import { useRef, useEffect } from 'react';
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  type MotionValue,
} from 'framer-motion';
import { IntakeForm } from './IntakeForm';
import { INTAKE_FIELDS, SECTION_LABELS } from './fields';

interface Props {
  onComplete: () => void;
}

function PrintedFormContent() {
  const sections = [...new Set(INTAKE_FIELDS.map(f => f.section))];
  return (
    <div style={{ fontFamily: '"Times New Roman", Georgia, serif' }}>
      <div className="text-center border-b-2 border-gray-700 pb-2 mb-2.5">
        <div className="text-[11px] font-bold uppercase tracking-widest text-gray-800">
          Valley Medical Center
        </div>
        <div className="text-[8.5px] uppercase tracking-wider text-gray-600 mt-0.5">
          Patient Intake Form — Please Print Clearly
        </div>
        <div className="text-[7px] text-gray-400 mt-0.5 italic">
          All information protected under HIPAA · Form #VMC-INT-2024
        </div>
      </div>

      {sections.map(section => (
        <div key={section} className="mb-2.5">
          <div
            className="text-[7.5px] font-bold uppercase tracking-widest text-blue-800 px-1.5 py-0.5 mb-1.5 border-l-[3px] border-blue-400"
            style={{ background: 'rgba(239,246,255,0.8)' }}
          >
            {SECTION_LABELS[section]}
          </div>
          {INTAKE_FIELDS.filter(f => f.section === section).map(field => (
            <div key={field.id} className="mb-1.5 pl-1">
              <div className="text-[7px] text-gray-500 leading-tight mb-0.5">
                {field.label}:
              </div>
              <div className="border-b border-gray-300 w-full" style={{ height: '10px' }} />
            </div>
          ))}
        </div>
      ))}

      <div className="mt-2.5 pt-2 border-t border-gray-300 flex gap-5">
        <div className="flex-1">
          <div className="border-b border-gray-600" style={{ height: '18px' }} />
          <div className="text-[6px] text-gray-400 mt-0.5 uppercase tracking-wider">Patient Signature</div>
        </div>
        <div style={{ width: '80px' }}>
          <div className="border-b border-gray-600" style={{ height: '18px' }} />
          <div className="text-[6px] text-gray-400 mt-0.5 uppercase tracking-wider">Date</div>
        </div>
      </div>

      <div className="mt-2 text-center" style={{ fontSize: '5.5px', color: '#9ca3af' }}>
        Valley Medical Center · 1400 Medical Plaza Dr · (555) 832-4000
      </div>
    </div>
  );
}

function ClipMetal({ opacity }: { opacity: MotionValue<number> }) {
  return (
    <motion.div
      style={{ opacity }}
      className="absolute left-1/2 -translate-x-1/2 -top-5 z-30 pointer-events-none select-none"
    >
      <svg width="156" height="60" viewBox="0 0 156 60" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="onb-body" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e5e7eb" />
            <stop offset="40%" stopColor="#9ca3af" />
            <stop offset="100%" stopColor="#6b7280" />
          </linearGradient>
          <linearGradient id="onb-handle" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#9ca3af" />
            <stop offset="50%" stopColor="#e5e7eb" />
            <stop offset="100%" stopColor="#9ca3af" />
          </linearGradient>
          <filter id="onb-shadow">
            <feDropShadow dx="0" dy="4" stdDeviation="5" floodColor="#000" floodOpacity="0.4" />
          </filter>
        </defs>

        {/* Main clip body */}
        <rect x="38" y="2" width="80" height="44" rx="8" fill="url(#onb-body)" filter="url(#onb-shadow)" />
        <rect x="42" y="6" width="72" height="36" rx="6" fill="#c8d0da" />
        <rect x="44" y="8" width="68" height="32" rx="5" fill="#dde3ea" />

        {/* Left handle wing */}
        <path d="M38 22 L5 13 L3 40 L38 36 Z" fill="url(#onb-handle)" />
        <path d="M38 22 L5 13 L3 40 L38 36 Z" stroke="#8d96a3" strokeWidth="0.5" fill="none" />

        {/* Right handle wing */}
        <path d="M118 22 L151 13 L153 40 L118 36 Z" fill="url(#onb-handle)" />
        <path d="M118 22 L151 13 L153 40 L118 36 Z" stroke="#8d96a3" strokeWidth="0.5" fill="none" />

        {/* Lower grip */}
        <rect x="53" y="38" width="50" height="18" rx="4" fill="#4b5563" />
        <rect x="55" y="40" width="46" height="14" rx="3" fill="#6b7280" />
        <rect x="55" y="40" width="10" height="14" rx="3" fill="rgba(255,255,255,0.1)" />

        {/* Bolt details */}
        {[56, 100].map(cx => (
          <g key={cx}>
            <circle cx={cx} cy="24" r="6" fill="#374151" />
            <circle cx={cx} cy="24" r="4" fill="#4b5563" />
            <circle cx={cx} cy="24" r="2.5" fill="#6b7280" />
            <circle cx={cx} cy="24" r="1" fill="#9ca3af" />
          </g>
        ))}

        {/* Sheen */}
        <rect x="44" y="8" width="14" height="32" rx="5" fill="rgba(255,255,255,0.2)" />
      </svg>
    </motion.div>
  );
}

export function OnboardingExperience({ onComplete }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: scrollRef,
    offset: ['start start', 'end end'],
  });

  const smooth = useSpring(scrollYProgress, { stiffness: 80, damping: 26, restDelta: 0.001 });

  // Main zoom transform
  const scale      = useTransform(smooth, [0, 0.75], [0.40, 1.02]);
  // Perspective tilt straightens as we approach
  const rotateX    = useTransform(smooth, [0, 0.52], [10, 0]);
  // Slight upward camera drift
  const translateY = useTransform(smooth, [0, 0.65], [32, 0]);

  // Clipboard board + clip dissolve
  const clipOpacity     = useTransform(smooth, [0.60, 0.82], [1, 0]);
  // Printed paper fades
  const printedOpacity  = useTransform(smooth, [0.70, 0.90], [1, 0]);
  // Interactive form fades in
  const interactiveOpacity = useTransform(smooth, [0.78, 0.97], [0, 1]);
  // Warm background fades to white
  const warmBgOpacity   = useTransform(smooth, [0.65, 0.92], [1, 0]);
  // Scroll hint disappears
  const hintOpacity     = useTransform(smooth, [0, 0.10], [1, 0]);
  // White wipe covers everything at the very end
  const whiteWipe       = useTransform(smooth, [0.93, 1.0], [0, 1]);

  useEffect(() => {
    return scrollYProgress.on('change', v => {
      if (v >= 0.985) onComplete();
    });
  }, [scrollYProgress, onComplete]);

  return (
    <div ref={scrollRef} style={{ height: '400vh' }}>
      {/* Sticky viewport — perspective parent */}
      <div
        className="sticky top-0 overflow-hidden flex items-center justify-center"
        style={{
          height: '100dvh',
          perspective: '1400px',
          perspectiveOrigin: '50% 45%',
        }}
      >
        {/* White base */}
        <div className="absolute inset-0 bg-white" />

        {/* Warm ambient desk background */}
        <motion.div
          style={{ opacity: warmBgOpacity }}
          className="absolute inset-0 pointer-events-none"
          aria-hidden
        >
          <div className="absolute inset-0 bg-gradient-to-b from-blue-100/50 via-slate-100 to-slate-200" />
          <div
            className="absolute inset-0"
            style={{
              background: 'radial-gradient(ellipse 75% 60% at 50% 38%, rgba(219,234,254,0.75) 0%, transparent 100%)',
            }}
          />
          {/* Subtle desk surface */}
          <div
            className="absolute bottom-0 left-0 right-0"
            style={{
              height: '38%',
              background: 'linear-gradient(to top, rgba(175,163,145,0.22), transparent)',
            }}
          />
        </motion.div>

        {/* ── Clipboard assembly ── */}
        <motion.div
          style={{
            scale,
            rotateX,
            y: translateY,
            transformOrigin: 'center 50%',
          }}
          className="relative z-10"
        >
          {/* Board dimensions: 480 × 650 */}
          <div style={{ width: 480, height: 650, position: 'relative' }}>

            {/* Wooden clipboard board */}
            <motion.div
              style={{ opacity: clipOpacity }}
              className="absolute inset-0 rounded-xl pointer-events-none"
              aria-hidden
            >
              <div
                className="absolute inset-0 rounded-xl"
                style={{
                  background: 'linear-gradient(158deg, #d6a84e 0%, #c48b34 28%, #b87526 52%, #c48b34 74%, #d6a84e 100%)',
                  boxShadow: '0 32px 100px rgba(0,0,0,0.5), 0 8px 30px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -1px 0 rgba(0,0,0,0.12)',
                }}
              />
              {/* Wood grain overlay */}
              <div
                className="absolute inset-0 rounded-xl opacity-20"
                style={{
                  backgroundImage: [
                    'repeating-linear-gradient(94deg, transparent, transparent 14px, rgba(0,0,0,0.04) 14px, rgba(0,0,0,0.04) 28px)',
                    'repeating-linear-gradient(87deg, transparent, transparent 50px, rgba(0,0,0,0.025) 50px, rgba(0,0,0,0.025) 100px)',
                  ].join(','),
                }}
              />
              {/* Bottom lip shadow */}
              <div
                className="absolute bottom-0 left-2 right-2 rounded-b-xl"
                style={{
                  height: '20px',
                  background: 'linear-gradient(to top, rgba(0,0,0,0.28), transparent)',
                }}
              />
              {/* Edge highlight */}
              <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/12" />
            </motion.div>

            {/* Metal spring clip */}
            <ClipMetal opacity={clipOpacity} />

            {/* Paper block: 440 × 578, offset 36px top, 20px sides */}
            <div
              style={{
                position: 'absolute',
                top: 36,
                left: 20,
                width: 440,
                height: 578,
                background: '#fff',
                borderRadius: '2px',
                overflow: 'hidden',
              }}
            >
              {/* Paper shadow (tied to clipboard) */}
              <motion.div
                style={{ opacity: clipOpacity }}
                className="absolute inset-0 pointer-events-none"
                aria-hidden
              >
                <div
                  className="absolute inset-0"
                  style={{ boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.06), 2px 3px 12px rgba(0,0,0,0.15)' }}
                />
              </motion.div>

              {/* Subtle ruled-line texture */}
              <div
                className="absolute inset-0 pointer-events-none"
                style={{
                  backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 23px, rgba(59,130,246,0.05) 23px, rgba(59,130,246,0.05) 24px)',
                  backgroundPositionY: '44px',
                }}
                aria-hidden
              />

              {/* Static printed form */}
              <motion.div
                style={{ opacity: printedOpacity }}
                className="absolute inset-0 p-5 overflow-hidden"
              >
                <PrintedFormContent />
              </motion.div>

              {/* Interactive intake form */}
              <motion.div
                style={{ opacity: interactiveOpacity }}
                className="absolute inset-0 overflow-y-auto overscroll-contain"
              >
                <IntakeForm inOnboarding />
              </motion.div>
            </div>
          </div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          style={{ opacity: hintOpacity }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3 pointer-events-none select-none"
        >
          <span
            className="text-xs font-medium uppercase"
            style={{ letterSpacing: '0.22em', color: 'rgba(100,116,139,0.75)' }}
          >
            Scroll to begin
          </span>
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ repeat: Infinity, duration: 2.2, ease: 'easeInOut' }}
            className="text-slate-400"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 5v14M5 12l7 7 7-7"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.div>
        </motion.div>

        {/* White wipe — covers everything at the end of scroll */}
        <motion.div
          style={{ opacity: whiteWipe }}
          className="absolute inset-0 bg-white pointer-events-none z-50"
          aria-hidden
        />
      </div>
    </div>
  );
}
