'''Студенты, рубрикатор и оценки'''
from dataclasses import dataclass
from math import isfinite


def validate_number(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} должно быть числом!')
    try:
        valid = isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{name} должно быть конечным числом!')


def validate_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} не может быть пустым!')
    return value.strip()


@dataclass(frozen=True)
class Student:
    student_id: str
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'student_id', validate_text(self.student_id, 'Номер студента'))
        object.__setattr__(self, 'name', validate_text(self.name, 'Имя студента'))


@dataclass(frozen=True)
class Criterion:
    criterion_id: str
    name: str
    max_score: float
    weight: float

    def __post_init__(self) -> None:
        object.__setattr__(self, 'criterion_id', validate_text(self.criterion_id, 'Номер критерия'))
        object.__setattr__(self, 'name', validate_text(self.name, 'Название критерия'))
        validate_number(self.max_score, 'Максимальное количество баллов')
        validate_number(self.weight, 'Значение веса')
        if self.max_score <= 0 or self.weight <= 0:
            raise ValueError('Максимальный балл и вес должны быть положительными!')


@dataclass(frozen=True)
class Score:
    value: float
    max_score: float

    def __post_init__(self) -> None:
        validate_number(self.value, 'Количество баллов')
        validate_number(self.max_score, 'Максимальное количество баллов')
        if self.max_score <= 0 or not 0 <= self.value <= self.max_score:
            raise ValueError('Балл должен находиться в диапазоне от 0 до максимума критерия!')


@dataclass(frozen=True)
class Evaluation:
    student_id: str
    criterion_id: str
    score: Score
    comment: str = ''

    def __post_init__(self) -> None:
        object.__setattr__(self, 'student_id', validate_text(self.student_id, 'Номер студента'))
        object.__setattr__(self, 'criterion_id', validate_text(self.criterion_id, 'Номер критерия'))
        if not isinstance(self.score, Score):
            raise ValueError('Оценка должна содержать объект Score!')
        if not isinstance(self.comment, str):
            raise ValueError('Комментарий должен быть строкой!')
        object.__setattr__(self, 'comment', self.comment.strip())


class EvaluationFactory:
    def create(self, student: Student, criterion: Criterion, value: float, comment: str = '') -> Evaluation:
        return Evaluation(student.student_id, criterion.criterion_id, Score(value, criterion.max_score), comment)


class Course:
    def __init__(self, evaluation_factory: EvaluationFactory) -> None:
        self._evaluation_factory = evaluation_factory
        self._students: dict[str, Student] = {}
        self._criteria: dict[str, Criterion] = {}
        self._evaluations: dict[tuple[str, str], Evaluation] = {}

    @property
    def students(self) -> tuple[Student, ...]:
        return tuple(self._students.values())

    @property
    def criteria(self) -> tuple[Criterion, ...]:
        return tuple(self._criteria.values())

    @property
    def evaluations(self) -> tuple[Evaluation, ...]:
        return tuple(self._evaluations.values())

    def get_student(self, student_id: str) -> Student:
        student_id = validate_text(student_id, 'Номер студента')
        if student_id not in self._students:
            raise ValueError('Студент не найден!')
        return self._students[student_id]

    def get_criterion(self, criterion_id: str) -> Criterion:
        criterion_id = validate_text(criterion_id, 'Номер критерия')
        if criterion_id not in self._criteria:
            raise ValueError('Критерий не найден в рубрикаторе!')
        return self._criteria[criterion_id]

    def add_student(self, student: Student) -> None:
        if not isinstance(student, Student):
            raise ValueError('Ожидался студент!')
        if student.student_id in self._students:
            raise ValueError('Номер студента уже занят!')
        self._students[student.student_id] = student

    def add_criterion(self, criterion: Criterion) -> None:
        if not isinstance(criterion, Criterion):
            raise ValueError('Ожидался критерий!')
        if criterion.criterion_id in self._criteria:
            raise ValueError('Номер критерия уже занят!')
        self._criteria[criterion.criterion_id] = criterion

    def rename_student(self, student_id: str, name: str) -> None:
        student = self.get_student(student_id)
        self._students[student.student_id] = Student(student.student_id, name)

    def update_criterion(self, criterion_id: str, name: str, max_score: float, weight: float) -> None:
        current = self.get_criterion(criterion_id)
        criterion = Criterion(current.criterion_id, name, max_score, weight)
        evaluations = self._evaluations.copy()
        for key, evaluation in self._evaluations.items():
            if evaluation.criterion_id == criterion.criterion_id:
                evaluations[key] = self._evaluation_factory.create(self.get_student(evaluation.student_id), criterion, evaluation.score.value, evaluation.comment)
        self._criteria[criterion.criterion_id] = criterion
        self._evaluations = evaluations

    def remove_student(self, student_id: str) -> None:
        student = self.get_student(student_id)
        if any(evaluation.student_id == student.student_id for evaluation in self.evaluations):
            raise ValueError('Сначала отмените оценки этого студента!')
        del self._students[student.student_id]

    def remove_criterion(self, criterion_id: str) -> None:
        criterion = self.get_criterion(criterion_id)
        if any(evaluation.criterion_id == criterion.criterion_id for evaluation in self.evaluations):
            raise ValueError('Сначала отмените оценки по этому критерию!')
        del self._criteria[criterion.criterion_id]

    def set_evaluation(self, student_id: str, criterion_id: str, value: float, comment: str = '') -> Evaluation:
        student = self.get_student(student_id)
        criterion = self.get_criterion(criterion_id)
        evaluation = self._evaluation_factory.create(student, criterion, value, comment)
        self._evaluations[(student.student_id, criterion.criterion_id)] = evaluation
        return evaluation

    def remove_evaluation(self, student_id: str, criterion_id: str) -> None:
        student = self.get_student(student_id)
        criterion = self.get_criterion(criterion_id)
        key = (student.student_id, criterion.criterion_id)
        if key not in self._evaluations:
            raise ValueError('Оценка не найдена!')
        del self._evaluations[key]

    def student_evaluations(self, student_id: str) -> tuple[Evaluation, ...]:
        student = self.get_student(student_id)
        return tuple(evaluation for evaluation in self.evaluations if evaluation.student_id == student.student_id)
