import json
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from .errors import InvalidInput, ModelUnavailable
from .ports import TextModel, TicketSource
from .schemas import PeriodInput, Topic, TopicsReport

CAPABILITY = "topics-report"


def validate(period: PeriodInput) -> None:
    if period.start > period.end:
        raise InvalidInput("A data inicial é posterior à data final")


def topics(period: PeriodInput, model: TextModel, tickets: TicketSource, tickets_per_call: int,
           concurrency: int, deadline_seconds: float,
           on_progress: Callable[[int, int], None] = lambda done, total: None) -> TopicsReport:
    """Monta o relatório de temas do período.

    O período inteiro não cabe numa chamada: os tickets vão em lotes, até `concurrency`
    lotes ao mesmo tempo. Os resultados são somados na ordem dos lotes, então o relatório
    é o mesmo da execução sequencial. Se um lote falha ou o prazo estoura, os lotes que
    ainda não começaram são cancelados e o erro sobe.
    """
    validate(period)
    selected = tickets.in_period(period.start, period.end)
    batches = [selected[i:i + tickets_per_call] for i in range(0, len(selected), tickets_per_call)]
    total, done = len(selected), 0
    on_progress(0, total)

    def run(batch: list[dict]) -> list[dict]:
        content = "\n".join(f"[{t['id']}] {t['text']}" for t in batch)
        return json.loads(model.complete(CAPABILITY, "topics", content))["topics"]

    executor = ThreadPoolExecutor(max_workers=max(1, concurrency), thread_name_prefix="topics")
    try:
        futures = {executor.submit(run, batch): len(batch) for batch in batches}
        pending = set(futures)
        deadline = time.monotonic() + deadline_seconds
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ModelUnavailable(f"O relatório não terminou em {deadline_seconds:.0f} s")
            finished, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
            for future in finished:
                future.result()  # propaga a primeira falha
                done += futures[future]
            on_progress(done, total)
        answers = [future.result() for future in futures]
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    totals: dict[str, dict] = {}
    for answer in answers:
        for item in answer:
            current = totals.setdefault(item["topic"], {"count": 0, "examples": []})
            current["count"] += item["count"]
            current["examples"] = (current["examples"] + item["examples"])[:3]

    items = [Topic(topic=name, **data) for name, data in totals.items()]
    items.sort(key=lambda t: (-t.count, t.topic))
    return TopicsReport(start=period.start, end=period.end, total_tickets=total, topics=items)
