# Shared field contract — field IDs must match client/src/fields.ts exactly.

INTAKE_FIELDS: dict[str, str] = {
    "patient-name":             "Patient's full legal name",
    "date-of-birth":            "Date of birth, format MM/DD/YYYY",
    "phone-number":             "Patient's phone number",
    "reason-for-visit":         "Primary reason for today's visit",
    "medical-conditions":       "Existing medical conditions or diagnoses",
    "current-medications":      "Current medications by name",
    "medication-dosages":       "Dosage for each medication",
    "allergies":                "Drug or food allergies",
    "allergy-reactions":        "Type of reaction for each allergy",
    "insurance-provider":       "Health insurance company name",
    "member-id":                "Insurance member ID number",
    "group-number":             "Insurance group number",
    "emergency-name":           "Emergency contact full name",
    "emergency-relationship":   "Relationship to patient",
    "emergency-phone":          "Emergency contact phone number",
}

REQUIRED_FIELDS: list[str] = [
    "patient-name",
    "date-of-birth",
    "phone-number",
    "reason-for-visit",
    "allergies",
    "insurance-provider",
    "member-id",
    "emergency-name",
    "emergency-phone",
]
