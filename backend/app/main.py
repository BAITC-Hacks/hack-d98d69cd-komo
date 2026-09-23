from contextlib import asynccontextmanager
import logging
import time
from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.db import Session, get_db, engine
from app.core.errors import AppError
from app.core.state import get_state
from app.core.cache import cache
from app.features.catalog.router import router as catalog
from app.features.identity.router import router as identity
from app.features.employees.router import router as employees
from app.features.recommendations.router import router as recommendations
from app.features.hr_analytics.router import router as hr
from app.features.data_import.router import router as imports

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpx2').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with Session() as db:
        state = await get_state(db)
        app.state.session_secret = settings().session_secret or state.session_secret
    yield
    await cache.aclose()
    await engine.dispose()


app = FastAPI(title='Career Quest API', version='1.0.0', lifespan=lifespan, docs_url='/api/v1/docs', openapi_url='/api/v1/openapi.json')


@app.exception_handler(AppError)
async def app_error(request: Request, error: AppError):
    return JSONResponse(status_code=error.status, content={'code': error.code, 'message': error.message, 'details': error.details})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return JSONResponse(status_code=422, content={'code': 'validation_error', 'message': 'Проверьте заполненные поля',
                                                'details': [{'field': '.'.join(map(str, e['loc'])), 'message': e['msg']} for e in error.errors()]})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    logging.getLogger(__name__).error('Unhandled request error: %s', type(error).__name__)
    return JSONResponse(status_code=500, content={'code': 'internal_error', 'message': 'Сервис временно недоступен. Повторите запрос.', 'details': None})


@app.middleware('http')
async def request_policy(request: Request, call_next):
    started = time.monotonic()
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        origin = request.headers.get('origin')
        if origin and origin.rstrip('/') not in settings().allowed_origins:
            return JSONResponse(status_code=403, content={'code': 'invalid_origin', 'message': 'Недопустимый источник запроса', 'details': None})
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse(status_code=403, content={'code': 'invalid_origin', 'message': 'Межсайтовый запрос запрещен', 'details': None})
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Response-Time-Ms'] = str(round((time.monotonic() - started) * 1000))
    return response


for router in (identity, catalog, employees, recommendations, hr, imports):
    app.include_router(router, prefix='/api/v1')


@app.get('/api/v1/health')
async def health():
    return {'status': 'ok'}


@app.get('/api/v1/ready')
async def ready(db: AsyncSession = Depends(get_db)):
    await db.execute(text('SELECT 1'))
    return {'status': 'ready', 'database': 'ok'}
