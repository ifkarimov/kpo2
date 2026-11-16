'''Правила расчёта итогового балла'''
from math import fsum
from typing import Protocol

from domain.models import Course, Criterion, Evaluation


class ScoreStrategy(Protocol):
    def calculate(self, criteria: tuple[Criterion, ...], evaluations: tuple[Evaluation, ...]) -> float: ...


class WeightedScore:
    def calculate(self, criteria: tuple[Criterion, ...], evaluations: tuple[Evaluation, ...]) -> float:
        scores = {evaluation.criterion_id: evaluation.score.value for evaluation in evaluations}
        largest_weight = max(criterion.weight for criterion in criteria)
        total_weight = fsum(criterion.weight / largest_weight for criterion in criteria)
        result = fsum(scores.get(criterion.criterion_id, 0) / criterion.max_score * (criterion.weight / largest_weight) / total_weight for criterion in criteria)
        return min(10.0, max(0.0, 10 * result))


class CompleteScore:
    def calculate(self, criteria: tuple[Criterion, ...], evaluations: tuple[Evaluation, ...]) -> float:
        evaluated = {evaluation.criterion_id for evaluation in evaluations}
        if any(criterion.criterion_id not in evaluated for criterion in criteria):
            raise ValueError('Для окончательного итога нужны оценки по всем критериям!')
        return WeightedScore().calculate(criteria, evaluations)


class ResultService:
    def __init__(self, strategy: ScoreStrategy) -> None:
        self._strategy = strategy

    def calculate(self, course: Course, student_id: str) -> float:
        evaluations = course.student_evaluations(student_id)
        if not course.criteria:
            raise ValueError('Нельзя рассчитать итог без критериев!')
        return self._strategy.calculate(course.criteria, evaluations)
