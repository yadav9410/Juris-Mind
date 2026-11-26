from enum import Enum


class LegalDomain(str, Enum):
    CONSTITUTIONAL = "constitutional"
    CRIMINAL = "criminal"
    CIVIL_PROCEDURE = "civil_procedure"
    CONTRACT = "contract"
    CORPORATE = "corporate"
    EMPLOYMENT_LABOUR = "employment_labour"
    PROPERTY = "property"
    FAMILY = "family"
    TAX = "tax"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    CONSUMER = "consumer"
    ENVIRONMENT = "environment"
    BANKING_FINANCE = "banking_finance"
    INSOLVENCY = "insolvency"
    REGULATORY = "regulatory"
    ADMINISTRATIVE = "administrative"
    EVIDENCE = "evidence"
    OTHER = "other"


class SourceType(str, Enum):
    LEGISLATION = "legislation"
    JUDGMENT = "judgment"
    GAZETTE_NOTIFICATION = "gazette_notification"
    COURT_RECORD = "court_record"
    SECONDARY_RESEARCH = "secondary_research"
    USER_DOCUMENT = "user_document"


class SourceTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    USER_SUPPLIED = "user_supplied"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_CLARIFICATION = "needs_clarification"
