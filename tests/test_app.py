import csv
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from application.ports import ResultExporter
from application.services import EvaluationFacade
from container import Container, build_container
from domain.models import EvaluationFactory, Student
from domain.ports import CourseRepository
from domain.services import CompleteScore, ScoreStrategy
from infrastructure.storage import course_to_data
from main import run_demo, run_menu


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'course.json'
        self.container = build_container(str(self.path))
        self.app = self.container.resolve(EvaluationFacade)
        self.app.add_student('S1', 'Иван')
        self.app.add_criterion('HW', 'ДЗ', 10, 1)
        self.app.set_evaluation('S1', 'HW', 8, 'Комментарий')

    def test_json_round_trip(self):
        app = build_container(str(self.path)).resolve(EvaluationFacade)
        self.assertEqual(app.students(), self.app.students())
        self.assertEqual(app.criteria(), self.app.criteria())
        self.assertEqual(app.evaluations('S1'), self.app.evaluations('S1'))
        self.assertEqual(app.total('S1'), 8)

    def test_invalid_change_does_not_touch_file(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.app.set_evaluation('S1', 'HW', 12)
        self.assertEqual(self.path.read_bytes(), before)

    def test_crud_is_persisted(self):
        self.app.rename_student('S1', 'Пётр')
        self.app.update_criterion('HW', 'Практика', 20, 2)
        self.assertEqual(self.app.students()[0].name, 'Пётр')
        self.assertEqual(self.app.total('S1'), 4)
        self.app.remove_evaluation('S1', 'HW')
        self.app.remove_student('S1')
        self.app.remove_criterion('HW')
        app = build_container(str(self.path)).resolve(EvaluationFacade)
        self.assertEqual(app.students(), ())
        self.assertEqual(app.criteria(), ())

    def test_csv_export(self):
        path = Path(self.directory.name) / 'results.csv'
        self.app.export_results(str(path))
        with path.open(encoding='utf-8-sig', newline='') as file:
            rows = list(csv.DictReader(file, delimiter=';'))
        self.assertEqual(rows, [dict(student_id='S1', name='Иван', total='8.00')])

    def test_csv_handles_delimiters_and_newlines(self):
        self.app.rename_student('S1', 'Иван; Петров\nБПИ252')
        path = Path(self.directory.name) / 'results.csv'
        self.app.export_results(str(path))
        with path.open(encoding='utf-8-sig', newline='') as file:
            row = next(csv.DictReader(file, delimiter=';'))
        self.assertEqual(row['name'], 'Иван; Петров\nБПИ252')

    def test_export_cannot_overwrite_database_or_existing_file(self):
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.app.export_results(str(self.path))
        self.assertEqual(self.path.read_bytes(), original)
        path = Path(self.directory.name) / 'results.csv'
        path.write_text('Старый отчёт', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.app.export_results(str(path))
        self.assertEqual(path.read_text(encoding='utf-8'), 'Старый отчёт')

    def test_import_replaces_whole_course(self):
        self.app.import_course(str(Path(__file__).resolve().parents[1] / 'examples' / 'course.json'))
        self.assertEqual(len(self.app.students()), 2)
        self.assertAlmostEqual(self.app.total('S1'), 8.4)
        self.assertAlmostEqual(self.app.total('S2'), 7.6)

    def test_invalid_import_preserves_current_data(self):
        original = self.path.read_bytes()
        path = Path(self.directory.name) / 'bad.json'
        wrong_score = json.loads(original)
        wrong_score['evaluations'][0]['score'] = 12
        unknown_criterion = json.loads(original)
        unknown_criterion['evaluations'][0]['criterion_id'] = 'UNKNOWN'
        duplicate = json.loads(original)
        duplicate['evaluations'].append(duplicate['evaluations'][0].copy())
        duplicate_student = json.loads(original)
        duplicate_student['students'].append(duplicate_student['students'][0].copy())
        invalid_student = json.loads(original)
        invalid_student['students'][0] = 5
        wrong_fields = json.loads(original)
        wrong_fields['evaluations'][0]['extra'] = 1
        for data in ([], {}, dict(students={}, criteria=[], evaluations=[]), wrong_score, unknown_criterion, duplicate, duplicate_student, invalid_student, wrong_fields):
            with self.subTest(data=data):
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.app.import_course(str(path))
                self.assertEqual(self.path.read_bytes(), original)

    def test_broken_json_is_not_replaced_by_empty_course(self):
        self.path.write_text('{bad json', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.app.add_student('S2', 'Анна')
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{bad json')

    def test_json_cannot_bypass_finite_number_validation(self):
        data = json.loads(self.path.read_text(encoding='utf-8'))
        data['evaluations'][0]['score'] = float('nan')
        self.path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.app.total('S1')

    def test_failed_save_keeps_previous_file_and_cleans_temporary(self):
        original = self.path.read_bytes()
        with patch('infrastructure.storage.Path.replace', side_effect=OSError('Нет доступа')):
            with self.assertRaises(OSError):
                self.app.set_evaluation('S1', 'HW', 9)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_memory_repository_returns_independent_copy(self):
        container = build_container(None)
        repository = container.resolve(CourseRepository)
        course = repository.get()
        course.add_student(Student('S1', 'Иван'))
        self.assertEqual(repository.get().students, ())
        repository.save(course)
        course.rename_student('S1', 'Пётр')
        self.assertEqual(repository.get().students[0].name, 'Иван')

    def test_memory_and_json_repositories_have_same_data(self):
        memory = build_container(None).resolve(CourseRepository)
        json_repository = self.container.resolve(CourseRepository)
        memory.save(json_repository.get())
        self.assertEqual(course_to_data(memory.get()), course_to_data(json_repository.get()))

    def test_strategy_can_be_replaced_in_container(self):
        self.app.add_criterion('EXAM', 'Экзамен', 20, 1)
        self.assertAlmostEqual(self.app.total('S1'), 4)
        self.container.register_instance(ScoreStrategy, CompleteScore())
        app = self.container.resolve(EvaluationFacade)
        with self.assertRaises(ValueError):
            app.total('S1')

    def test_exporter_can_be_replaced_in_container(self):
        exporter = Mock(spec=ResultExporter)
        self.container.register_instance(ResultExporter, exporter)
        app = self.container.resolve(EvaluationFacade)
        app.export_results('results.csv')
        exporter.export.assert_called_once_with(app.results(), 'results.csv')

    def test_complete_export_does_not_create_partial_report(self):
        self.app.add_student('S2', 'Анна')
        app = build_container(str(self.path), complete=True).resolve(EvaluationFacade)
        path = Path(self.directory.name) / 'results.csv'
        with self.assertRaises(ValueError):
            app.export_results(str(path))
        self.assertFalse(path.exists())

    def test_container_missing_registration(self):
        with self.assertRaises(ValueError):
            Container().resolve(EvaluationFacade)

    def test_registered_instances_are_shared(self):
        self.assertIs(self.container.resolve(CourseRepository), self.container.resolve(CourseRepository))
        self.assertIs(self.container.resolve(EvaluationFactory), self.container.resolve(EvaluationFactory))


class ConsoleTests(unittest.TestCase):
    def run_inputs(self, values):
        app = build_container(None).resolve(EvaluationFacade)
        output = io.StringIO()
        with patch('builtins.input', side_effect=values), redirect_stdout(output):
            run_menu(app)
        return app, output.getvalue()

    def test_full_console_scenario(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'results.csv'
            values = ['1', 'S1', 'Иван', '2', 'HW', 'ДЗ', '10', '0,4', '2', 'EXAM', 'Экзамен', '20', '0,6', '5', 'S1', 'HW', '9', '', '5', 'S1', 'EXAM', '16', '', '3', '4', '6', 'S1', '8', 'S1', '9', '10', str(path), '0']
            app, output = self.run_inputs(values)
            self.assertAlmostEqual(app.total('S1'), 8.4)
            self.assertIn('8.40/10', output)
            self.assertTrue(path.exists())
            self.assertNotIn('Ошибка:', output)

    def test_console_correction_and_removal(self):
        values = ['1', 'S1', 'Иван', '2', 'HW', 'ДЗ', '10', '1', '5', 'S1', 'HW', '8', '', '5', 'S1', 'HW', '9', '', '12', 'S1', 'Пётр', '13', 'HW', 'Практика', '20', '1', '8', 'S1', '7', 'S1', 'HW', '14', 'S1', '15', 'HW', '0']
        app, output = self.run_inputs(values)
        self.assertEqual(app.students(), ())
        self.assertEqual(app.criteria(), ())
        self.assertIn('4.50/10', output)
        self.assertNotIn('Ошибка:', output)

    def test_input_errors_do_not_stop_menu(self):
        values = ['unknown', '2', 'HW', 'ДЗ', 'abc', '1', '', 'Иван', '2', 'HW', 'ДЗ', 'nan', '1', '5', 'UNKNOWN', 'HW', '5', '', '0']
        app, output = self.run_inputs(values)
        self.assertEqual(app.students(), ())
        self.assertEqual(app.criteria(), ())
        self.assertIn('Неизвестная команда', output)
        self.assertEqual(output.count('Ошибка:'), 4)

    def test_empty_lists(self):
        _, output = self.run_inputs(['3', '4', '9', '0'])
        self.assertIn('Пока пусто', output)
        self.assertIn('Студентов пока нет', output)

    def test_demo(self):
        with TemporaryDirectory() as directory:
            app = build_container(None).resolve(EvaluationFacade)
            path = Path(directory) / 'results.csv'
            with redirect_stdout(io.StringIO()) as output:
                run_demo(app, str(path))
            self.assertAlmostEqual(app.total('S1'), 8.4)
            self.assertAlmostEqual(app.total('S2'), 7.6)
            self.assertEqual(output.getvalue().count('Отклонено:'), 2)
            self.assertTrue(path.exists())

    def test_import_confirmed_or_cancelled(self):
        path = str(Path(__file__).resolve().parents[1] / 'examples' / 'course.json')
        app, _ = self.run_inputs(['11', path, 'нет', '0'])
        self.assertEqual(app.students(), ())
        app, output = self.run_inputs(['11', path, 'да', '0'])
        self.assertEqual(len(app.students()), 2)
        self.assertIn('Ведомость импортирована', output)

    def test_eof_and_interrupt_exit_cleanly(self):
        for error in (EOFError(), KeyboardInterrupt()):
            with self.subTest(error=error):
                _, output = self.run_inputs([error])
                self.assertIn('Выход', output)


if __name__ == '__main__':
    unittest.main()
