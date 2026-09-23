from typing import Literal
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.errors import AppError
from app.features.identity.models import User
from app.features.identity.service import hr_user
from app.features.data_import.schemas import ImportResult
from app.features.data_import.service import import_data
from app.features.data_import.formats import TEMPLATE_DIR, decode_file, merge_uploads

router = APIRouter(prefix='/hr', tags=['data_import'])


async def read_file(file: UploadFile | None) -> bytes | None:
    if file is None:
        return None
    content = await file.read(4 * 1024 * 1024 + 1)
    if len(content) > 4 * 1024 * 1024:
        raise AppError('file_too_large', 'Размер одного файла не более 4 МБ', 413)
    return content


@router.post('/import', response_model=ImportResult)
async def upload(employees: UploadFile | None = File(None), history: UploadFile | None = File(None),
                 user: User = Depends(hr_user), db: AsyncSession = Depends(get_db)):
    parts = []
    for file, kind in [(employees, 'employees'), (history, 'history')]:
        if file:
            raw = await read_file(file)
            parts.append(await run_in_threadpool(decode_file, raw, file.filename, kind))
    return await import_data(db, *merge_uploads(parts))


@router.get('/import/template')
async def template(format: Literal['xlsx', 'json'] = 'xlsx', user: User = Depends(hr_user)):
    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if format == 'xlsx' else 'application/json'
    return FileResponse(TEMPLATE_DIR / f'career-quest-template.{format}', media_type=mime,
                        filename=f'career-quest-template.{format}')
