// Shared field contract — IDs must match server/intake_fields.py exactly

export const INTAKE_FIELDS = [
  { id: "patient-name",           label: "Full Legal Name",         type: "text",     section: "personal"    },
  { id: "date-of-birth",          label: "Date of Birth",           type: "date",     section: "personal"    },
  { id: "phone-number",           label: "Phone Number",            type: "tel",      section: "personal"    },
  { id: "reason-for-visit",       label: "Reason for Visit",        type: "textarea", section: "visit"       },
  { id: "medical-conditions",     label: "Existing Conditions",     type: "textarea", section: "visit"       },
  { id: "current-medications",    label: "Current Medications",     type: "textarea", section: "medications" },
  { id: "medication-dosages",     label: "Dosages",                 type: "textarea", section: "medications" },
  { id: "allergies",              label: "Allergies",               type: "textarea", section: "allergies"   },
  { id: "allergy-reactions",      label: "Reaction Types",          type: "textarea", section: "allergies"   },
  { id: "insurance-provider",     label: "Insurance Provider",      type: "text",     section: "insurance"   },
  { id: "member-id",              label: "Member ID",               type: "text",     section: "insurance"   },
  { id: "group-number",           label: "Group Number",            type: "text",     section: "insurance"   },
  { id: "emergency-name",         label: "Emergency Contact Name",  type: "text",     section: "emergency"   },
  { id: "emergency-relationship", label: "Relationship",            type: "text",     section: "emergency"   },
  { id: "emergency-phone",        label: "Emergency Phone",         type: "tel",      section: "emergency"   },
] as const;

export type FieldId = typeof INTAKE_FIELDS[number]["id"];

export const SECTION_LABELS: Record<string, string> = {
  personal:    "Personal Information",
  visit:       "Reason for Visit",
  medications: "Medications",
  allergies:   "Allergies",
  insurance:   "Insurance",
  emergency:   "Emergency Contact",
};
