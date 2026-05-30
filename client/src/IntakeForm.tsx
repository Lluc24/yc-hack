import { useEffect } from "react";
import { INTAKE_FIELDS, SECTION_LABELS } from "./fields";

interface IntakeFormProps {
  /** Compact variant used inside the onboarding clipboard */
  inOnboarding?: boolean;
}

export function IntakeForm({ inOnboarding = false }: IntakeFormProps) {
  const sections = [...new Set(INTAKE_FIELDS.map((f) => f.section))];

  // Auto-focus first field after fade-in when embedded in onboarding
  useEffect(() => {
    if (!inOnboarding) return;
    const t = setTimeout(() => {
      (document.getElementById("patient-name") as HTMLInputElement | null)?.focus();
    }, 350);
    return () => clearTimeout(t);
  }, [inOnboarding]);

  const outerClass = inOnboarding
    ? "w-full bg-white"
    : "max-w-2xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden";

  const headerPadding = inOnboarding ? "px-4 py-2.5" : "px-6 py-4";
  const titleSize = inOnboarding ? "text-sm" : "text-xl";
  const subtitleSize = inOnboarding ? "text-xs" : "text-sm";
  const formPadding = inOnboarding ? "p-4 space-y-5" : "p-6 space-y-8";
  const hintPadding = inOnboarding ? "px-4 py-1.5 text-xs" : "px-6 py-2 text-xs";

  return (
    <div className={outerClass}>
      {/* Portal header */}
      <div className={`bg-blue-700 ${headerPadding} flex items-center justify-between`}>
        <div>
          <div className={`text-white font-semibold ${titleSize}`}>Valley Medical Center</div>
          <div className={`text-blue-200 ${subtitleSize}`}>Pre-Visit Patient Intake — MyChart</div>
        </div>
        <div className="text-blue-200 text-xs text-right">
          <div>Secure Form</div>
          <div className="mt-0.5 opacity-70">All fields encrypted</div>
        </div>
      </div>

      {/* Progress hint */}
      <div className={`bg-blue-50 border-b border-blue-100 ${hintPadding} text-blue-600`}>
        Please speak naturally — ClearPath will fill in each field as you talk.
      </div>

      <form
        id="intake-form"
        className={formPadding}
        onSubmit={(e) => e.preventDefault()}
      >
        {sections.map((section) => (
          <div key={section}>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest border-b border-gray-100 pb-2 mb-4">
              {SECTION_LABELS[section]}
            </h2>
            <div className="space-y-4">
              {INTAKE_FIELDS.filter((f) => f.section === section).map((field) => (
                <div key={field.id}>
                  <label
                    htmlFor={field.id}
                    className="block text-sm font-medium text-gray-600 mb-1"
                  >
                    {field.label}
                  </label>
                  {field.type === "textarea" ? (
                    <textarea
                      id={field.id}
                      name={field.id}
                      rows={2}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm
                                 text-gray-800 placeholder-gray-300
                                 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                                 transition-all duration-300 resize-none"
                      placeholder="Voice agent will fill this in..."
                    />
                  ) : (
                    <input
                      id={field.id}
                      name={field.id}
                      type={field.type}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm
                                 text-gray-800 placeholder-gray-300
                                 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                                 transition-all duration-300"
                      placeholder="Voice agent will fill this in..."
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        <button
          id="submit-intake"
          type="submit"
          className="w-full bg-blue-700 text-white py-3 rounded-lg font-semibold
                     hover:bg-blue-800 active:bg-blue-900 transition-colors"
        >
          Submit Intake Form
        </button>
      </form>
    </div>
  );
}
