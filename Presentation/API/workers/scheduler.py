# Presentation/API/workers/scheduler.py

import os
import time
import traceback
from typing import Dict, Any, Optional

import psycopg2
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from Presentation.API.settings import settings
from Presentation.API.workers.datasource_builder import run_pipeline_as_seed


# Um inteiro 64-bit fixo para identificar o lock global do job
PG_ADVISORY_LOCK_KEY = 987654321012345678  # int8


def _build_config_from_settings() -> Dict[str, Any]:
    """
    Config equivalente ao datasource_builder.build_config, mas local ao scheduler.
    (Se preferir, você pode simplesmente importar build_config do datasource_builder.)
    """
    return {
        "db": {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "dbname": settings.DB_NAME,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
        },
        "http": {
            "timeout_secs": settings.HTTP_TIMEOUT_SECS,
        },
        "schemas": {
            "target_schema": "zcm",
            "default_srid": 4674,
        },
        "endpoints": {
            "info": "https://pedea.sema.ce.gov.br/gestorapi/v1/infoDataExplorer",
            "txt_gestorapi": "https://pedea.sema.ce.gov.br/gestorapi/v1/arquivotxt/",
            "txt_portal": "https://pedea.sema.ce.gov.br/portal/metadata/",
            "txt_suffix": "_metadados.txt",
        },
    }


def _try_pg_advisory_lock(conn) -> bool:
    """
    Tenta pegar lock sem bloquear. Retorna True se conseguiu.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s);", (PG_ADVISORY_LOCK_KEY,))
        return bool(cur.fetchone()[0])


def _pg_advisory_unlock(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s);", (PG_ADVISORY_LOCK_KEY,))


def _get_pg_conn(db: Dict[str, Any]):
    return psycopg2.connect(**db)


def datasource_seed_job() -> None:
    """
    Job agendado (sincrono). Será executado pelo APScheduler.
    - Usa advisory lock para evitar duplicidade entre workers/replicas
    - Executa run_pipeline_as_seed()
    """
    # APScheduler chama em loop asyncio; essa função é sync e OK.
    cfg = _build_config_from_settings()
    db = cfg["db"]

    # Guardrail opcional: permitir desabilitar por env var
    if os.getenv("DISABLE_DATASOURCE_SEED", "").lower() in ("1", "true", "yes"):
        print("[Scheduler] DISABLE_DATASOURCE_SEED ativo. Job ignorado.")
        return

    conn = None
    locked = False
    try:
        conn = _get_pg_conn(db)
        conn.autocommit = True

        locked = _try_pg_advisory_lock(conn)
        if not locked:
            print("[Scheduler] Outro worker/container já está executando o seed. Ignorando.")
            return

        print("[Scheduler] Lock obtido. Executando run_pipeline_as_seed()...")
        rc = run_pipeline_as_seed()
        if rc == 0:
            print("[Scheduler] Seed OK (rc=0).")
        else:
            print(f"[Scheduler] Seed retornou erro (rc={rc}).")

    except Exception as e:
        print(f"[Scheduler] Erro no job: {e}")
        traceback.print_exc()
    finally:
        try:
            if conn and locked:
                _pg_advisory_unlock(conn)
                print("[Scheduler] Lock liberado.")
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def start_scheduler() -> AsyncIOScheduler:
    """
    Inicializa o scheduler com timezone America/Sao_Paulo e agenda o job às 03:00.
    """
    scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

    # roda diariamente às 03:00
    scheduler.add_job(
        datasource_seed_job,
        trigger="cron",
        hour=3,
        minute=0,
        id="datasource_seed_3am",
        replace_existing=True,
        max_instances=1,      # evita concorrência no mesmo scheduler
        coalesce=True,        # se perdeu execuções, "junta" em uma
        misfire_grace_time=3600,  # 1h de tolerância se o container estava ocupado
    )

    scheduler.start()
    print("[Scheduler] APScheduler iniciado. Job diário 03:00 agendado.")
    return scheduler
