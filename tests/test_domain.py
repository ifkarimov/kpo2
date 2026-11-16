import unittest
from dataclasses import FrozenInstanceError

from domain.models import Course, Criterion, EvaluationFactory, Score, Student
from domain.services import CompleteScore, ResultService, WeightedScore


class CourseTests(unittest.TestCase):
    def setUp(self):
        self.course = Course(EvaluationFactory())
        self.course.add_student(Student('S1', 'Иван'))
        self.course.add_criterion(Criterion('HW', 'Домашняя работа', 10, 2))
        self.course.add_criterion(Criterion('EXAM', 'Экзамен', 20, 3))
        self.service = ResultService(WeightedScore())

    def test_normalization(self):
        self.assertEqual(Student(' S2 ', ' Анна '), Student('S2', 'Анна'))
        self.course.set_evaluation(' S1 ', ' HW ', 7)
        self.assertEqual(self.course.student_evaluations(' S1 ')[0].score.value, 7)

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            self.course.add_student(Student(' S1 ', 'Другой студент'))
        with self.assertRaises(ValueError):
            self.course.add_criterion(Criterion(' HW ', 'Другой критерий', 20, 1))

    def test_unknown_student_or_criterion(self):
        for student_id, criterion_id in (('UNKNOWN', 'HW'), ('S1', 'UNKNOWN')):
            with self.subTest(student_id=student_id, criterion_id=criterion_id), self.assertRaises(ValueError):
                self.course.set_evaluation(student_id, criterion_id, 5)
        self.assertEqual(self.course.evaluations, ())

    def test_invalid_evaluation_preserves_previous(self):
        self.course.set_evaluation('S1', 'HW', 7)
        for value in (-1, 11, float('nan'), float('inf'), True, '5'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.course.set_evaluation('S1', 'HW', value)
            self.assertEqual(self.course.evaluations[0].score.value, 7)

    def test_score_boundaries_and_fraction(self):
        for value in (0, 7.5, 10):
            self.course.set_evaluation('S1', 'HW', value)
            self.assertEqual(self.course.evaluations[0].score.value, value)

    def test_invalid_comment_preserves_evaluation(self):
        self.course.set_evaluation('S1', 'HW', 5)
        with self.assertRaises(ValueError):
            self.course.set_evaluation('S1', 'HW', 8, None)
        self.assertEqual(self.course.evaluations[0].score.value, 5)

    def test_weighted_total(self):
        self.course.set_evaluation('S1', 'HW', 9)
        self.course.set_evaluation('S1', 'EXAM', 16)
        self.assertAlmostEqual(self.service.calculate(self.course, 'S1'), 8.4)

    def test_total_follows_corrections_and_cancellation(self):
        self.course.set_evaluation('S1', 'HW', 10)
        self.course.set_evaluation('S1', 'EXAM', 20)
        self.assertAlmostEqual(self.service.calculate(self.course, 'S1'), 10)
        self.course.set_evaluation('S1', 'HW', 5)
        self.assertAlmostEqual(self.service.calculate(self.course, 'S1'), 8)
        self.assertEqual(len(self.course.evaluations), 2)
        self.course.remove_evaluation('S1', 'EXAM')
        self.assertAlmostEqual(self.service.calculate(self.course, 'S1'), 2)

    def test_no_scores_means_zero(self):
        self.assertEqual(self.service.calculate(self.course, 'S1'), 0)

    def test_empty_rubric_and_unknown_student(self):
        with self.assertRaises(ValueError):
            self.service.calculate(self.course, 'UNKNOWN')
        self.course.remove_criterion('HW')
        self.course.remove_criterion('EXAM')
        with self.assertRaises(ValueError):
            self.service.calculate(self.course, 'S1')

    def test_complete_strategy(self):
        service = ResultService(CompleteScore())
        self.course.set_evaluation('S1', 'HW', 9)
        with self.assertRaises(ValueError):
            service.calculate(self.course, 'S1')
        self.course.set_evaluation('S1', 'EXAM', 0)
        self.assertAlmostEqual(service.calculate(self.course, 'S1'), 3.6)

    def test_criterion_update_checks_every_evaluation_before_change(self):
        self.course.add_student(Student('S2', 'Анна'))
        self.course.set_evaluation('S1', 'HW', 3)
        self.course.set_evaluation('S2', 'HW', 9)
        before = self.course.evaluations
        with self.assertRaises(ValueError):
            self.course.update_criterion('HW', 'Новое название', 5, 8)
        self.assertEqual(self.course.evaluations, before)
        self.assertEqual(self.course.get_criterion('HW'), Criterion('HW', 'Домашняя работа', 10, 2))

    def test_criterion_update_changes_total_and_score_scale(self):
        self.course.set_evaluation('S1', 'HW', 10)
        self.course.update_criterion('HW', 'Практика', 20, 3)
        self.assertEqual(self.course.evaluations[0].score, Score(10, 20))
        self.assertAlmostEqual(self.service.calculate(self.course, 'S1'), 2.5)

    def test_adding_criterion_changes_current_total(self):
        self.course.set_evaluation('S1', 'HW', 10)
        self.course.set_evaluation('S1', 'EXAM', 20)
        self.course.add_criterion(Criterion('TEST', 'Тест', 5, 5))
        self.assertAlmostEqual(self.service.calculate(self.course, 'S1'), 5)

    def test_remove_requires_cancelling_evaluations(self):
        self.course.set_evaluation('S1', 'HW', 7)
        with self.assertRaises(ValueError):
            self.course.remove_student('S1')
        with self.assertRaises(ValueError):
            self.course.remove_criterion('HW')
        self.course.remove_evaluation('S1', 'HW')
        self.course.remove_student('S1')
        self.course.remove_criterion('HW')
        self.assertEqual(self.course.students, ())
        self.assertEqual(len(self.course.criteria), 1)

    def test_rename_preserves_student_evaluations(self):
        self.course.set_evaluation('S1', 'HW', 7)
        self.course.rename_student('S1', 'Пётр')
        self.assertEqual(self.course.get_student('S1').name, 'Пётр')
        self.assertEqual(len(self.course.student_evaluations('S1')), 1)

    def test_missing_evaluation_cannot_be_removed(self):
        with self.assertRaises(ValueError):
            self.course.remove_evaluation('S1', 'HW')

    def test_domain_objects_cannot_be_mutated_through_properties(self):
        self.course.set_evaluation('S1', 'HW', 7)
        with self.assertRaises(FrozenInstanceError):
            self.course.students[0].student_id = 'S2'
        with self.assertRaises(FrozenInstanceError):
            self.course.evaluations[0].score.value = 100
        self.assertIsInstance(self.course.criteria, tuple)

    def test_large_weights_do_not_overflow(self):
        self.course.update_criterion('HW', 'ДЗ', 10, 1e308)
        self.course.update_criterion('EXAM', 'Экзамен', 20, 1e308)
        self.course.set_evaluation('S1', 'HW', 10)
        self.course.set_evaluation('S1', 'EXAM', 20)
        self.assertAlmostEqual(self.service.calculate(self.course, 'S1'), 10)


class ModelTests(unittest.TestCase):
    def test_invalid_names_and_ids(self):
        for student_id, name in (('', 'Иван'), ('S1', '  '), (None, 'Иван')):
            with self.subTest(student_id=student_id, name=name), self.assertRaises(ValueError):
                Student(student_id, name)
        with self.assertRaises(ValueError):
            Criterion('C1', '', 10, 1)

    def test_invalid_maximum_and_weight(self):
        for value in (0, -1, True, '10', float('nan'), float('inf'), 10 ** 1000):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Criterion('C1', 'Критерий', value, 1)
                with self.assertRaises(ValueError):
                    Criterion('C1', 'Критерий', 10, value)

    def test_score_value_equality(self):
        self.assertEqual(Score(5, 10), Score(5, 10))
        self.assertNotEqual(Score(5, 10), Score(5, 20))

    def test_score_cannot_bypass_validation(self):
        for value, maximum in ((11, 10), (0, 0), (1, float('nan')), (True, 10)):
            with self.subTest(value=value, maximum=maximum), self.assertRaises(ValueError):
                Score(value, maximum)


if __name__ == '__main__':
    unittest.main()
