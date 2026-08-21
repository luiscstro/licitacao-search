"""
Observabilidade: tracing (OpenTelemetry) e monitoramento de erros (Sentry).

Tudo aqui é opcional e zero-config por padrão — não exige nenhuma conta
externa nem custa nada pra rodar localmente:

- Tracing sempre roda com um `ConsoleSpanExporter` (spans impressos no
  terminal) — dá pra ver o que tá acontecendo sem configurar nada. Se você
  tiver um coletor OTLP rodando (ex: Jaeger, um coletor local, um serviço
  gratuito), defina OTEL_EXPORTER_OTLP_ENDPOINT que os spans também são
  exportados pra lá.
- Sentry só é ativado se a variável SENTRY_DSN estiver definida — sem ela,
  `setup_observability` não faz nada relacionado a Sentry (nenhuma chamada de
  rede, nenhum SDK inicializado).
"""

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

SERVICE_NAME_VALUE = "licittracker-backend"


def _setup_tracing(app: FastAPI) -> None:
    resource = Resource.create({SERVICE_NAME: SERVICE_NAME_VALUE})
    provider = TracerProvider(resource=resource)

    # Sempre exporta pro console — funciona offline, sem custo, sem conta.
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    # Se quiser mandar os spans pra um coletor OTLP (Jaeger, Tempo, etc.),
    # defina OTEL_EXPORTER_OTLP_ENDPOINT. Import fica dentro do if pra não
    # pagar o custo (nem exigir a dependência funcionando) quando não usado.
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


def _setup_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return  # sem DSN = no-op total, nenhum SDK inicializado, nenhuma rede

    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    )


def setup_observability(app: FastAPI) -> None:
    """Chamada única, logo depois de `app = FastAPI(...)`, que liga tracing
    (sempre, via console — e via OTLP se configurado) e Sentry (só se
    SENTRY_DSN estiver definida)."""
    _setup_tracing(app)
    _setup_sentry()
