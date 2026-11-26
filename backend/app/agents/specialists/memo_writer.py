"""Mock-first Memo Writer specialist."""
from app.agents.base import MockSpecialistAgent


class MemoWriter(MockSpecialistAgent):
    key = "memo_writer"
    display_name = "Memo Writer"
    description = "Organize supplied findings into a memo-ready structure without adding unsupported law."
