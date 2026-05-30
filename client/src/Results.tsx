import { useEffect, useState } from "react";
import { INTAKE_FIELDS, SECTION_LABELS } from "./fields";

const API_URL = "http://localhost:8000";

interface IntakeRecord {
  session_id: string;
  fields: Record<string, string>;
  timestamp: string;
  source?: string;
}

function formatTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export function Results() {
  const [intakes, setIntakes] = useState<IntakeRecord[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    const load = () =>
      fetch(`${API_URL}/api/intakes`)
        .then((r) => r.json())
        .then((d) => { setIntakes(d.intakes ?? []); setError(false); })
        .catch(() => setError(true));
    load();
    const interval = setInterval(load, 5000); // poll every 5s
    return () => clearInterval(interval);
  }, []);

  const sections = [...new Set(INTAKE_FIELDS.map((f) => f.section))];

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Valley Medical Center</h1>
            <p className="text-sm text-gray-500">Submitted Patient Intakes — Staff View</p>
          </div>
          <span className="bg-blue-700 text-white text-sm font-medium px-3 py-1 rounded-full">
            {intakes.length} record{intakes.length !== 1 ? "s" : ""}
          </span>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 mb-4">
            Cannot reach the intake API at {API_URL}. Is intake_backend running on port 8000?
          </div>
        )}

        {!error && intakes.length === 0 && (
          <div className="text-center text-gray-400 mt-24">
            No intake records yet. Completed forms (web or phone) will appear here automatically.
          </div>
        )}

        {/* Records */}
        <div className="space-y-6">
          {intakes.map((record) => (
            <div key={record.session_id} className="bg-white rounded-xl shadow overflow-hidden">
              {/* Card header */}
              <div className="bg-blue-700 px-5 py-3 flex items-center justify-between">
                <span className="text-white font-semibold text-lg">
                  {record.fields["patient-name"] || "Unknown Patient"}
                </span>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    record.source === "phone"
                      ? "bg-amber-300 text-amber-900"
                      : "bg-blue-300 text-blue-900"
                  }`}>
                    {record.source === "phone" ? "📞 Phone" : "🌐 Web"}
                  </span>
                  <span className="text-blue-200 text-xs">{formatTime(record.timestamp)}</span>
                </div>
              </div>

              {/* Card body — grouped by section */}
              <div className="p-5 space-y-4">
                {sections.map((section) => {
                  const sectionFields = INTAKE_FIELDS.filter(
                    (f) => f.section === section && record.fields[f.id]
                  );
                  if (sectionFields.length === 0) return null;
                  return (
                    <div key={section}>
                      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
                        {SECTION_LABELS[section]}
                      </h3>
                      <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                        {sectionFields.map((f) => (
                          <div key={f.id}>
                            <dt className="text-gray-400 text-xs">{f.label}</dt>
                            <dd className="text-gray-800">{record.fields[f.id]}</dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
