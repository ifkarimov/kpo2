'''Консольное меню и запуск'''
import argparse

from application.services import EvaluationFacade
from container import build_container


def read_number(prompt: str) -> float:
    try:
        return float(input(prompt).replace(',', '.'))
    except ValueError as error:
        raise ValueError('Введите число!') from error


def add_student(app: EvaluationFacade) -> None:
    student_id = input('Номер студента: ')
    name = input('Имя студента: ')
    app.add_student(student_id, name)
    print('Студент добавлен')


def add_criterion(app: EvaluationFacade) -> None:
    criterion_id = input('Номер критерия: ')
    name = input('Название критерия: ')
    max_score = read_number('Максимальный балл: ')
    weight = read_number('Вес: ')
    app.add_criterion(criterion_id, name, max_score, weight)
    print('Критерий добавлен')


def show_students(app: EvaluationFacade) -> None:
    students = app.students()
    print('\nСтуденты:')
    if not students:
        print('Пока пусто')
    for student in students:
        print(f'{student.student_id}: {student.name}')


def show_criteria(app: EvaluationFacade) -> None:
    criteria = app.criteria()
    print('\nРубрикатор:')
    if not criteria:
        print('Пока пусто')
    for criterion in criteria:
        print(f'{criterion.criterion_id}: {criterion.name}; максимум {criterion.max_score:g}; вес {criterion.weight:g}')


def set_evaluation(app: EvaluationFacade) -> None:
    student_id = input('Номер студента: ')
    criterion_id = input('Номер критерия: ')
    value = read_number('Балл: ')
    comment = input('Комментарий (можно оставить пустым): ')
    app.set_evaluation(student_id, criterion_id, value, comment)
    print('Оценка сохранена')


def show_evaluations(app: EvaluationFacade) -> None:
    student_id = input('Номер студента: ')
    evaluations = app.evaluations(student_id)
    if not evaluations:
        print('Оценок пока нет')
    names = {criterion.criterion_id: criterion.name for criterion in app.criteria()}
    for evaluation in evaluations:
        print(f'{evaluation.criterion_id}: {names[evaluation.criterion_id]}; {evaluation.score.value:g}/{evaluation.score.max_score:g}; {evaluation.comment}')


def remove_evaluation(app: EvaluationFacade) -> None:
    student_id = input('Номер студента: ')
    criterion_id = input('Номер критерия: ')
    app.remove_evaluation(student_id, criterion_id)
    print('Оценка отменена')


def show_total(app: EvaluationFacade) -> None:
    student_id = input('Номер студента: ')
    print(f'Итог: {app.total(student_id):.2f}/10')


def show_results(app: EvaluationFacade) -> None:
    rows = app.results()
    if not rows:
        print('Студентов пока нет')
    for row in rows:
        print(f'{row.student_id}: {row.name}; итог {row.total:.2f}/10')


def export_results(app: EvaluationFacade) -> None:
    path = input('Путь к новому CSV-файлу: ').strip()
    if not path:
        raise ValueError('Путь не может быть пустым!')
    app.export_results(path)
    print(f'Итоги экспортированы: {path}')


def import_course(app: EvaluationFacade) -> None:
    path = input('Путь к JSON-ведомости: ').strip()
    if not path:
        raise ValueError('Путь не может быть пустым!')
    if input('Импорт заменит текущих студентов, критерии и оценки. Продолжить? (да/нет): ').strip().lower() != 'да':
        print('Импорт отменён')
        return
    app.import_course(path)
    print('Ведомость импортирована')


def rename_student(app: EvaluationFacade) -> None:
    student_id = input('Номер студента: ')
    name = input('Новое имя: ')
    app.rename_student(student_id, name)
    print('Имя изменено')


def update_criterion(app: EvaluationFacade) -> None:
    criterion_id = input('Номер критерия: ')
    name = input('Новое название: ')
    max_score = read_number('Новый максимальный балл: ')
    weight = read_number('Новый вес: ')
    app.update_criterion(criterion_id, name, max_score, weight)
    print('Критерий изменён')


def remove_student(app: EvaluationFacade) -> None:
    app.remove_student(input('Номер студента: '))
    print('Студент удалён')


def remove_criterion(app: EvaluationFacade) -> None:
    app.remove_criterion(input('Номер критерия: '))
    print('Критерий удалён')


def run_demo(app: EvaluationFacade, export_path: str) -> None:
    print('=== Демонстрация «ПОС» ===')
    app.add_student('S1', 'Иван Петров')
    app.add_student('S2', 'Анна Смирнова')
    app.add_criterion('HW', 'Домашние задания', 10, 0.4)
    app.add_criterion('EXAM', 'Экзамен', 20, 0.6)
    show_students(app)
    show_criteria(app)
    app.set_evaluation('S1', 'HW', 9, 'Хорошая работа')
    app.set_evaluation('S1', 'EXAM', 16)
    app.set_evaluation('S2', 'HW', 7)
    app.set_evaluation('S2', 'EXAM', 18)
    print('\nОценки выставлены. Исправляем оценку S2 за домашние задания на 10:')
    app.set_evaluation('S2', 'HW', 10)
    print('Отменяем оценку S2 за экзамен и выставляем заново: 12/20')
    app.remove_evaluation('S2', 'EXAM')
    app.set_evaluation('S2', 'EXAM', 12)
    print('\nПопытки нарушить правила:')
    for criterion_id, value in (('HW', 12), ('UNKNOWN', 5)):
        try:
            app.set_evaluation('S1', criterion_id, value)
        except ValueError as error:
            print(f'Отклонено: {error}')
    print('\nИтоги:')
    show_results(app)
    app.export_results(export_path)
    print(f'Итоги экспортированы: {export_path}')


def run_menu(app: EvaluationFacade) -> None:
    actions = {'1': add_student, '2': add_criterion, '3': show_students, '4': show_criteria, '5': set_evaluation, '6': show_evaluations, '7': remove_evaluation, '8': show_total, '9': show_results, '10': export_results, '11': import_course, '12': rename_student, '13': update_criterion, '14': remove_student, '15': remove_criterion}
    while True:
        print('\n1 - Добавить студента\n2 - Добавить критерий\n3 - Студенты\n4 - Рубрикатор\n5 - Выставить или исправить оценку\n6 - Оценки студента\n7 - Отменить оценку\n8 - Итог студента\n9 - Все итоги\n10 - Экспорт итогов в CSV\n11 - Импорт ведомости из JSON\n12 - Изменить имя студента\n13 - Изменить критерий\n14 - Удалить студента\n15 - Удалить критерий\n0 - Выход')
        try:
            choice = input('Выберите действие: ').strip()
            if choice == '0':
                return
            if choice not in actions:
                print('Неизвестная команда!')
                continue
            actions[choice](app)
        except (ValueError, OSError) as error:
            print(f'Ошибка: {error}')
        except (EOFError, KeyboardInterrupt):
            print('\nВыход')
            return


def main() -> int:
    parser = argparse.ArgumentParser(description = 'Преподавательская оценка студентов «ПОС»')
    parser.add_argument('--demo', action = 'store_true', help = 'демонстрация на отдельных данных в памяти')
    parser.add_argument('--data', default = 'data/course.json', help = 'путь к JSON-хранилищу')
    parser.add_argument('--export', default = 'demo_results.csv', help = 'новый CSV-файл для результатов демонстрации')
    parser.add_argument('--complete', action = 'store_true', help = 'рассчитывать итог только при наличии всех оценок')
    args = parser.parse_args()
    app = build_container(None if args.demo else args.data, args.complete).resolve(EvaluationFacade)
    try:
        if args.demo:
            run_demo(app, args.export)
        else:
            app.students()
            print('Режим: окончательный итог' if args.complete else 'Режим: текущий итог, пропущенные оценки считаются нулевыми')
            run_menu(app)
    except (ValueError, OSError) as error:
        print(f'Ошибка: {error}')
        return 1
    except (EOFError, KeyboardInterrupt):
        print('\nВыход')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
