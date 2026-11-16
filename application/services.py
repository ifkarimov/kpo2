'''Сценарии работы с курсом'''
from application.ports import CourseImporter, ResultExporter, ResultRow
from domain.models import Criterion, Evaluation, Student
from domain.ports import CourseRepository
from domain.services import ResultService


class EvaluationFacade:
    def __init__(self, repository: CourseRepository, result_service: ResultService, exporter: ResultExporter, importer: CourseImporter) -> None:
        self._repository = repository
        self._result_service = result_service
        self._exporter = exporter
        self._importer = importer

    def add_student(self, student_id: str, name: str) -> None:
        course = self._repository.get()
        course.add_student(Student(student_id, name))
        self._repository.save(course)

    def add_criterion(self, criterion_id: str, name: str, max_score: float, weight: float) -> None:
        course = self._repository.get()
        course.add_criterion(Criterion(criterion_id, name, max_score, weight))
        self._repository.save(course)

    def rename_student(self, student_id: str, name: str) -> None:
        course = self._repository.get()
        course.rename_student(student_id, name)
        self._repository.save(course)

    def update_criterion(self, criterion_id: str, name: str, max_score: float, weight: float) -> None:
        course = self._repository.get()
        course.update_criterion(criterion_id, name, max_score, weight)
        self._repository.save(course)

    def remove_student(self, student_id: str) -> None:
        course = self._repository.get()
        course.remove_student(student_id)
        self._repository.save(course)

    def remove_criterion(self, criterion_id: str) -> None:
        course = self._repository.get()
        course.remove_criterion(criterion_id)
        self._repository.save(course)

    def set_evaluation(self, student_id: str, criterion_id: str, value: float, comment: str = '') -> None:
        course = self._repository.get()
        course.set_evaluation(student_id, criterion_id, value, comment)
        self._repository.save(course)

    def remove_evaluation(self, student_id: str, criterion_id: str) -> None:
        course = self._repository.get()
        course.remove_evaluation(student_id, criterion_id)
        self._repository.save(course)

    def students(self) -> tuple[Student, ...]:
        return self._repository.get().students

    def criteria(self) -> tuple[Criterion, ...]:
        return self._repository.get().criteria

    def evaluations(self, student_id: str) -> tuple[Evaluation, ...]:
        return self._repository.get().student_evaluations(student_id)

    def total(self, student_id: str) -> float:
        return self._result_service.calculate(self._repository.get(), student_id)

    def results(self) -> tuple[ResultRow, ...]:
        course = self._repository.get()
        return tuple(ResultRow(student.student_id, student.name, self._result_service.calculate(course, student.student_id)) for student in course.students)

    def export_results(self, path: str) -> None:
        self._exporter.export(self.results(), path)

    def import_course(self, path: str) -> None:
        course = self._importer.read(path)
        self._repository.save(course)
