import csv
import io
import json
from datetime import date
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError
from app.core.state import get_state
from app.features.catalog.service import load_catalog
from app.features.employees.models import Employee
from app.features.development.models import ActivityRecord
from app.features.development.schemas import HistoryInput
from app.features.data_import.schemas import EmployeeBundle, ImportResult

HISTORY_COLUMNS = ['record_id', 'employee_id', 'event_id', 'date', 'due_date', 'status', 'completion_pct', 'score', 'feedback_rating', 'assigned_by']


def validation_details(error: ValidationError):
    # Never echo raw input values or exceptions in validation responses.
    return [{'field': '.'.join(map(str, e['loc'])), 'message': e['msg']} for e in error.errors(include_input=False, include_context=False)]


def parse_history(raw: bytes) -> list[dict]:
    try:
        text = raw.decode('utf-8-sig')
        first_line = text.splitlines()[0] if text.splitlines() else ''
        delimiter = ';' if first_line.count(';') > first_line.count(',') else ','
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        fields = [f.strip() for f in reader.fieldnames or []]
        if len(fields) != len(HISTORY_COLUMNS) or set(fields) != set(HISTORY_COLUMNS):
            raise AppError('invalid_csv_header', 'CSV должен содержать колонки истории; порядок может быть любым', 422, {'columns': HISTORY_COLUMNS})
        reader.fieldnames = fields
        rows = []
        for line, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                raise AppError('invalid_csv_row', f'CSV, строка {line}: количество значений не совпадает с колонками', 422)
            row = {k: v.strip() for k, v in row.items()}
            if len(rows) >= 20000:
                raise AppError('import_too_large', 'Не более 20 000 записей за импорт', 413)
            try:
                normalized = {k: (None if v == '' and k in ('due_date', 'score', 'feedback_rating') else v) for k, v in row.items()}
                rows.append(HistoryInput.model_validate(normalized).model_dump(mode='json'))
            except ValidationError as error:
                raise AppError('invalid_history', f'Ошибка в CSV, строка {line}', 422, validation_details(error))
        if not rows:
            raise AppError('empty_history', 'CSV не содержит записей', 422)
        return rows
    except UnicodeDecodeError:
        raise AppError('invalid_encoding', 'Файл должен быть в UTF-8', 422)


async def import_data(db: AsyncSession, employees_raw: bytes | None, history_raw: bytes | None) -> ImportResult:
    if not employees_raw and not history_raw:
        raise AppError('files_required', 'Выберите Excel, JSON профилей или файл истории с непустыми данными', 422)
    state = await get_state(db, lock=True)
    incoming_employees = []
    if employees_raw:
        try:
            bundle = EmployeeBundle.model_validate_json(employees_raw)
        except ValidationError as error:
            raise AppError('invalid_employees', 'Ошибка в JSON профилей', 422, validation_details(error))
        if bundle.meta.as_of_date != state.as_of_date or bundle.meta.dataset != 'Career Quest' or bundle.meta.version != '1.0':
            raise AppError('incompatible_dataset', 'Ожидается Career Quest 1.0 с датой среза 2026-10-01', 422)
        incoming_employees = [e.model_dump(mode='json') for e in bundle.employees]
    history = parse_history(history_raw) if history_raw else []
    catalog = await load_catalog(db)
    current_employees = {e.employee_id: e for e in (await db.scalars(select(Employee))).all()}
    combined = {k: e.data for k, e in current_employees.items()} | {e['employee_id']: e for e in incoming_employees}
    for label, rows, id_key in [('профили', incoming_employees, 'employee_id'), ('история', history, 'record_id')]:
        if len({r[id_key] for r in rows}) != len(rows):
            raise AppError('duplicate_ids', f'Повторяющиеся идентификаторы в файле: {label}', 422)
    for e in incoming_employees:
        errors = []
        if (e['role'], e['grade']) not in catalog.roles:
            errors.append('Неизвестная роль или грейд')
        if e['career_goal'] and (e['career_goal']['target_role'], e['career_goal']['target_grade']) not in catalog.roles:
            errors.append('Неизвестная карьерная цель')
        if set(e['skills']) - catalog.skills.keys():
            errors.append('Неизвестные идентификаторы навыков')
        if e['last_review_date'] > state.as_of_date.isoformat():
            errors.append('Дата оценки находится после даты среза')
        manager = combined.get(e['manager_id']) if e['manager_id'] else None
        if e['manager_id'] and (not manager or manager['grade'] != 'Lead' or manager['department'] != e['department'] or e['manager_id'] == e['employee_id']):
            errors.append('Некорректная ссылка на руководителя')
        if errors:
            raise AppError('invalid_profile_references', 'Ошибка в профиле ' + e['employee_id'], 422, errors)
    # Validate the resulting graph, including existing employees affected by an updated manager.
    for e in combined.values():
        if e['manager_id']:
            manager = combined.get(e['manager_id'])
            if not manager or manager['grade'] != 'Lead' or manager['department'] != e['department']:
                raise AppError('invalid_manager_graph', 'Обновление нарушает связь с руководителем: ' + e['employee_id'], 422)
    existing_records = {r.record_id: r for r in (await db.scalars(select(ActivityRecord).where(ActivityRecord.record_id.in_([r['record_id'] for r in history])))).all()} if history else {}
    for r in history:
        event = catalog.events.get(r['event_id'])
        if r['employee_id'] not in combined or not event:
            raise AppError('unknown_reference', 'Неизвестный сотрудник или активность: ' + r['record_id'], 422)
        if r['date'] > state.as_of_date.isoformat() or r['date'] < combined[r['employee_id']]['hire_date']:
            raise AppError('invalid_history_date', 'Недопустимая дата участия: ' + r['record_id'], 422)
        if r['status'] == 'no_show' and event['format'] == 'self_paced':
            raise AppError('invalid_status', 'no_show недопустим для self-paced: ' + r['record_id'], 422)
        if r['status'] == 'overdue' and (not event['mandatory'] or not r['due_date'] or r['due_date'] >= state.as_of_date.isoformat()):
            raise AppError('invalid_status', 'Некорректная просрочка: ' + r['record_id'], 422)
        if r['due_date'] and (not event['mandatory'] or r['due_date'] < r['date']):
            raise AppError('invalid_due_date', 'Некорректный дедлайн: ' + r['record_id'], 422)
        existing = existing_records.get(r['record_id'])
        if existing and existing.data.get('completed_at'):
            raise AppError('local_completion_conflict', 'Импорт не может перезаписать выполнение, подтвержденное в приложении: ' + r['record_id'], 409)
    ec = eu = hc = hu = 0
    for e in incoming_employees:
        existing = current_employees.get(e['employee_id'])
        if existing:
            if existing.data != e:
                existing.data = e
                eu += 1
        else:
            db.add(Employee(employee_id=e['employee_id'], data=e))
            ec += 1
    await db.flush()
    for r in history:
        existing = existing_records.get(r['record_id'])
        if existing:
            if existing.data != r:
                existing.employee_id, existing.event_id, existing.date, existing.status, existing.data = r['employee_id'], r['event_id'], date.fromisoformat(r['date']), r['status'], r
                hu += 1
        else:
            db.add(ActivityRecord(record_id=r['record_id'], employee_id=r['employee_id'], event_id=r['event_id'], date=date.fromisoformat(r['date']), status=r['status'], data=r))
            hc += 1
    if ec + eu + hc + hu:
        state.revision += 1
    result = ImportResult(employees_created=ec, employees_updated=eu, history_created=hc, history_updated=hu, revision=state.revision,
                          employee_ids=sorted({e['employee_id'] for e in incoming_employees} | {r['employee_id'] for r in history}),
                          message='Импорт завершен' if ec + eu + hc + hu else 'Изменений нет: эти данные уже загружены')
    await db.commit()
    return result
