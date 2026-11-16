'''Создание и выдача зависимостей'''
from typing import Callable, TypeVar, cast

from application.ports import CourseImporter, ResultExporter
from application.services import EvaluationFacade
from domain.models import EvaluationFactory
from domain.ports import CourseRepository
from domain.services import CompleteScore, ResultService, ScoreStrategy, WeightedScore
from infrastructure.storage import CsvResultExporter, JsonCourseImporter, JsonCourseRepository, MemoryCourseRepository

T = TypeVar('T')


class Container:
    def __init__(self) -> None:
        self._providers: dict[type, Callable[['Container'], object]] = {}

    def register_instance(self, contract: type[T], instance: T) -> None:
        self._providers[contract] = lambda container: instance

    def register_factory(self, contract: type[T], factory: Callable[['Container'], T]) -> None:
        self._providers[contract] = factory

    def resolve(self, contract: type[T]) -> T:
        if contract not in self._providers:
            raise ValueError(f'Зависимость {contract.__name__} не зарегистрирована!')
        return cast(T, self._providers[contract](self))


def build_container(path: str | None = 'data/course.json', complete: bool = False) -> Container:
    container = Container()
    factory = EvaluationFactory()
    container.register_instance(EvaluationFactory, factory)
    repository = MemoryCourseRepository(factory) if path is None else JsonCourseRepository(path, factory)
    container.register_instance(CourseRepository, repository)
    container.register_instance(ScoreStrategy, CompleteScore() if complete else WeightedScore())
    container.register_instance(ResultExporter, CsvResultExporter(path))
    container.register_factory(CourseImporter, lambda c: JsonCourseImporter(c.resolve(EvaluationFactory)))
    container.register_factory(ResultService, lambda c: ResultService(c.resolve(ScoreStrategy)))
    container.register_factory(EvaluationFacade, lambda c: EvaluationFacade(c.resolve(CourseRepository), c.resolve(ResultService), c.resolve(ResultExporter), c.resolve(CourseImporter)))
    return container
