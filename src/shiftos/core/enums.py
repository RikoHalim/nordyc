from enum import StrEnum


class EvidenceClass(StrEnum):
    VERIFIED_UNIVERSITY_FACT = "verified_university_fact"
    PUBLISHED_STANDARD = "published_standard"
    OCCUPATION_REQUIREMENT = "occupation_requirement"
    DATED_WORKFORCE_SIGNAL = "dated_workforce_signal"
    DATED_AI_CAPABILITY = "dated_ai_capability"
    INFERENCE = "inference"
    SYNTHETIC_DEMO = "synthetic_demo"


class CourseType(StrEnum):
    COMPULSORY = "COMPULSORY"
    ELECTIVE = "ELECTIVE"
    UNKNOWN = "UNKNOWN"


class ExtractionStatus(StrEnum):
    INVENTORY_ONLY = "INVENTORY_ONLY"
    NORMALIZED_FIXTURE = "NORMALIZED_FIXTURE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DocumentKind(StrEnum):
    PROGRAMME_STRUCTURE = "PROGRAMME_STRUCTURE"
    SYLLABUS = "SYLLABUS"
    SUPPORTING = "SUPPORTING"


class DocumentFormat(StrEnum):
    PDF = "PDF"
    DOCX = "DOCX"
    JSON = "JSON"


class ContentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    NORMALIZED_FIXTURE = "NORMALIZED_FIXTURE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NEEDS_OCR = "NEEDS_OCR"
    FAILED = "FAILED"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
