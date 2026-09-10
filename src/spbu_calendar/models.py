from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Group:
    id: int
    name: str
    division: str


@dataclass(frozen=True)
class Lesson:
    source_id: str
    subject: str
    start: datetime
    end: datetime
    location: str = ""
    educator: str = ""
    cancelled: bool = False
    elective: bool = False
    facultative: bool = False
