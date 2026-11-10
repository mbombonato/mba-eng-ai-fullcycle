"""Avaliação local (não oficial) de um prompt YAML com as mesmas métricas de src/metrics.py.

Não cria experimento no LangSmith. Serve para medir o v1 sem sobrescrever o v2 público
e para iterar no v2 antes do push. A avaliação oficial continua sendo src/evaluate.py.

Uso (na raiz do desafio, com o .env preenchido):
    python3 scripts/eval_local.py prompts/bug_to_user_story_v1.yml
    python3 scripts/eval_local.py prompts/bug_to_user_story_v2.yml 4,9,10   # só alguns exemplos
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml
from dotenv import load_dotenv

sys.path.insert(0, "src")
load_dotenv()

from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

import metrics  # noqa: E402

prompt_file = sys.argv[1]
data = next(iter(yaml.safe_load(open(prompt_file, encoding="utf-8")).values()))
template = ChatPromptTemplate.from_messages(
    [("system", data["system_prompt"]), ("user", data["user_prompt"])]
)
llm = ChatOpenAI(model=os.environ["LLM_MODEL"], temperature=0)
rows = [json.loads(line) for line in open("datasets/bug_to_user_story.jsonl", encoding="utf-8")]
indices = [int(i) for i in sys.argv[2].split(",")] if len(sys.argv) > 2 else range(1, len(rows) + 1)


def run(i):
    question = rows[i - 1]["inputs"]["bug_report"]
    reference = rows[i - 1]["outputs"]["reference"]
    answer = (template | llm).invoke({"bug_report": question}).content
    return (
        i,
        metrics.evaluate_f1_score(question, answer, reference)["score"],
        metrics.evaluate_clarity(question, answer, reference)["score"],
        metrics.evaluate_precision(question, answer, reference)["score"],
    )


results = list(ThreadPoolExecutor(8).map(run, indices))
for i, f1, clarity, precision in results:
    print(f"[{i}] F1:{f1:.2f} Clarity:{clarity:.2f} Precision:{precision:.2f}")
n = len(results)
f1, clarity, precision = (sum(r[k] for r in results) / n for k in (1, 2, 3))
print(f"F1-Score: {f1:.2f} | Clarity: {clarity:.2f} | Precision: {precision:.2f}")
print(f"Helpfulness: {(clarity + precision) / 2:.2f} | Correctness: {(f1 + precision) / 2:.2f}")
