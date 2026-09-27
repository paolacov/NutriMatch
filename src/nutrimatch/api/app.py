"""FastAPI: puente HTTP sobre Catalog + RankingService. No recalcula D1/D2/D3."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nutrimatch import __version__
from nutrimatch.core.errors import ProductNotFoundError
from nutrimatch.db.connection import connect, init_db
from nutrimatch.db.repositories.event_log import EventLogRepository
from nutrimatch.db.repositories.ranking_run import RankingRunRepository
from nutrimatch.schemas.cart import CartSummary, CartSummaryRequest
from nutrimatch.schemas.event import EventCreate, EventRow
from nutrimatch.schemas.product import ExplainRequest, MetaResponse, ProductDetail
from nutrimatch.schemas.ranking import RankingItem, RankingRequest, RankingResult
from nutrimatch.services.cart import resumir_codes
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.product import detalle_desde_fila
from nutrimatch.services.ranking import RankingService, filtrar_por_query

SEARCH_LIMITE_POR_DEFECTO = 40


def create_app(
    *,
    catalog: Catalog | None = None,
    db_path: Path | None = None,
) -> FastAPI:
    cat = catalog if catalog is not None else Catalog.from_referencia()
    servicio = RankingService(cat)
    conexion = connect(db_path)
    init_db(conexion)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Iterator[None]:
        app.state.catalog = cat
        app.state.ranking = servicio
        app.state.db = conexion
        yield
        conexion.close()

    app = FastAPI(title="NutriMatch", version=__version__, lifespan=lifespan)
    app.state.catalog = cat
    app.state.ranking = servicio
    app.state.db = conexion
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:4200", "http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ProductNotFoundError)
    async def _producto_no_encontrado(_request: Request, exc: ProductNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validacion(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/meta", response_model=MetaResponse)
    def meta(request: Request) -> MetaResponse:
        cat: Catalog = request.app.state.catalog
        return MetaResponse(
            snapshot_id=cat.snapshot_id,
            engine_version=__version__,
            n_products=len(cat.df),
            n_puntuable=cat.n_puntuable(),
        )

    @app.get("/search", response_model=list[ProductDetail])
    def search(
        request: Request,
        q: str = "",
        limit: int = Query(default=SEARCH_LIMITE_POR_DEFECTO, ge=1, le=100),
    ) -> list[ProductDetail]:
        cat: Catalog = request.app.state.catalog
        filtrado = filtrar_por_query(cat.df, q)
        return [detalle_desde_fila(fila) for _, fila in filtrado.head(limit).iterrows()]

    @app.get("/products", response_model=list[ProductDetail])
    def products_by_codes(request: Request, codes: str = "") -> list[ProductDetail]:
        cat: Catalog = request.app.state.catalog
        pedidos = [c.strip() for c in codes.split(",") if c.strip()]
        encontrados: list[ProductDetail] = []
        for code in pedidos:
            coincidencias = cat.df.loc[cat.df["code"] == code]
            if coincidencias.empty:
                continue
            encontrados.append(detalle_desde_fila(coincidencias.iloc[0]))
        return encontrados

    @app.get("/products/{code}", response_model=ProductDetail)
    def product_detail(code: str, request: Request) -> ProductDetail:
        cat: Catalog = request.app.state.catalog
        return detalle_desde_fila(cat.get_row(code))

    @app.post("/ranking", response_model=RankingResult)
    def ranking(payload: RankingRequest, request: Request) -> RankingResult:
        servicio: RankingService = request.app.state.ranking
        resultado = servicio.rank(payload)
        run_id = RankingRunRepository(request.app.state.db).save(
            resultado, payload.profile.model_dump_json()
        )
        EventLogRepository(request.app.state.db).append(
            "ranking_run_created",
            {"ranking_run_id": run_id, "query": payload.query, "n_matched": resultado.n_matched},
        )
        return resultado

    @app.get("/events", response_model=list[EventRow])
    def list_events(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> list[EventRow]:
        return [EventRow.model_validate(fila) for fila in EventLogRepository(request.app.state.db).list(limit)]

    @app.post("/events", response_model=EventRow)
    def create_event(payload: EventCreate, request: Request) -> EventRow:
        repo = EventLogRepository(request.app.state.db)
        repo.append(payload.event_type, payload.payload)
        return EventRow.model_validate(repo.list(limit=1)[0])

    @app.post("/ranking/explain", response_model=RankingItem)
    def explain(payload: ExplainRequest, request: Request) -> RankingItem:
        servicio: RankingService = request.app.state.ranking
        return servicio.explain(payload.code, payload.profile)

    @app.post("/cart/summary", response_model=CartSummary)
    def cart_summary(payload: CartSummaryRequest, request: Request) -> CartSummary:
        cat: Catalog = request.app.state.catalog
        return resumir_codes(cat, payload.codes)

    return app
