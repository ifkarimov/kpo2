'''Порты импорта ведомости и экспорта итогов'''
from dataclasses import dataclass
from typing import Protocol

from domain.models import Course


@dataclass(frozen=True)
class ResultRow:
    student_id: str
    name: str
    total: float


class ResultExporter(Protocol):
    def export(self, rows: tuple[ResultRow, ...], path: str) -> None: ...


class CourseImporter(Protocol):
    def read(self, path: str) -> Course: ...
