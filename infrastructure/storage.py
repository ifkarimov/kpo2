'''JSON-хранилище, импорт и экспорт CSV'''
import csv
import json
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

from application.ports import ResultRow
from domain.models import Course, Criterion, EvaluationFactory, Student


def course_to_data(course: Course) -> dict:
    students = [dict(student_id = student.student_id, name = student.name) for student in course.students]
    criteria = [dict(criterion_id = criterion.criterion_id, name = criterion.name, max_score = criterion.max_score, weight = criterion.weight) for criterion in course.criteria]
    evaluations = [dict(student_id = evaluation.student_id, criterion_id = evaluation.criterion_id, score = evaluation.score.value, comment = evaluation.comment) for evaluation in course.evaluations]
    return dict(students = students, criteria = criteria, evaluations = evaluations)


def course_from_data(data: dict, factory: EvaluationFactory) -> Course:
    if not isinstance(data, dict) or set(data) != {'students', 'criteria', 'evaluations'}:
        raise ValueError('В JSON ожидаются students, criteria и evaluations!')
    if any(not isinstance(data[field], list) for field in data):
        raise ValueError('Студенты, критерии и оценки должны быть списками!')
    course = Course(factory)
    try:
        for item in data['students']:
            course.add_student(Student(**item))
        for item in data['criteria']:
            course.add_criterion(Criterion(**item))
        seen = set()
        for item in data['evaluations']:
            if not isinstance(item, dict) or not {'student_id', 'criterion_id', 'score'} <= set(item) or set(item) - {'student_id', 'criterion_id', 'score', 'comment'}:
                raise ValueError('Некорректная запись оценки!')
            evaluation = course.set_evaluation(item['student_id'], item['criterion_id'], item['score'], item.get('comment', ''))
            key = (evaluation.student_id, evaluation.criterion_id)
            if key in seen:
                raise ValueError('В ведомости повторяется оценка по одному критерию!')
            seen.add(key)
    except (TypeError, KeyError) as error:
        raise ValueError('Неверные поля в JSON-ведомости!') from error
    return course


def read_course(path: Path, factory: EvaluationFactory) -> Course:
    try:
        with path.open(encoding = 'utf-8') as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError('Файл содержит некорректный JSON!') from error
    return course_from_data(data, factory)


class MemoryCourseRepository:
    def __init__(self, factory: EvaluationFactory) -> None:
        self._course = Course(factory)

    def get(self) -> Course:
        return deepcopy(self._course)

    def save(self, course: Course) -> None:
        self._course = deepcopy(course)


class JsonCourseRepository:
    def __init__(self, path: str, factory: EvaluationFactory) -> None:
        self._path = Path(path)
        self._factory = factory

    def get(self) -> Course:
        if not self._path.exists():
            return Course(self._factory)
        return read_course(self._path, self._factory)

    def save(self, course: Course) -> None:
        self._path.parent.mkdir(parents = True, exist_ok = True)
        temporary = None
        try:
            with NamedTemporaryFile(mode = 'w', encoding = 'utf-8', dir = self._path.parent, delete = False) as file:
                temporary = Path(file.name)
                json.dump(course_to_data(course), file, ensure_ascii = False, indent = 4, allow_nan = False)
                file.write('\n')
            temporary.replace(self._path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok = True)


class JsonCourseImporter:
    def __init__(self, factory: EvaluationFactory) -> None:
        self._factory = factory

    def read(self, path: str) -> Course:
        return read_course(Path(path), self._factory)


class CsvResultExporter:
    def __init__(self, protected_path: str | None = None) -> None:
        self._protected_path = Path(protected_path).resolve() if protected_path is not None else None

    def export(self, rows: tuple[ResultRow, ...], path: str) -> None:
        destination = Path(path)
        if destination.resolve() == self._protected_path:
            raise ValueError('Нельзя записать CSV на место JSON-хранилища!')
        if destination.exists():
            raise ValueError('Файл экспорта уже существует. Выберите другое имя!')
        destination.parent.mkdir(parents = True, exist_ok = True)
        with destination.open('x', encoding = 'utf-8-sig', newline = '') as file:
            writer = csv.writer(file, delimiter = ';')
            writer.writerow(['student_id', 'name', 'total'])
            for row in rows:
                writer.writerow([row.student_id, row.name, f'{row.total:.2f}'])
