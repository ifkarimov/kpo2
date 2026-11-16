'''Порт хранения курса'''
from typing import Protocol

from domain.models import Course


class CourseRepository(Protocol):
    def get(self) -> Course: ...

    def save(self, course: Course) -> None: ...
