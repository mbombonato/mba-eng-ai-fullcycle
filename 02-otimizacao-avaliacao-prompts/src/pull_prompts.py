"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
vir de terceiros. Aqui o prompt é o semente do desafio, então o risco é conhecido.
"""

import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SOURCE_PROMPT = os.getenv("SOURCE_PROMPT", "leonanluppi/bug_to_user_story_v1")
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"


def _message_role(message) -> str:
    """Converte o tipo da mensagem do LangChain para o papel usado no YAML."""
    class_name = type(message).__name__.lower()
    if "system" in class_name:
        return "system"
    if "human" in class_name or "user" in class_name:
        return "user"
    if "ai" in class_name:
        return "assistant"
    return class_name


def _message_template(message) -> str:
    """Extrai o texto do template de uma mensagem do ChatPromptTemplate."""
    inner = getattr(message, "prompt", None)
    if inner is not None and hasattr(inner, "template"):
        return inner.template
    # Mensagens já formatadas (ex.: SystemMessage) guardam o texto em .content
    return str(getattr(message, "content", ""))


def prompt_to_dict(prompt) -> dict:
    """Serializa um ChatPromptTemplate no formato YAML usado pelo projeto."""
    system_parts, user_parts, others = [], [], []

    for message in prompt.messages:
        role = _message_role(message)
        text = _message_template(message)
        if role == "system":
            system_parts.append(text)
        elif role == "user":
            user_parts.append(text)
        else:
            others.append({"role": role, "template": text})

    data = {
        "description": "Prompt para converter relatos de bugs em User Stories",
        "system_prompt": "\n\n".join(system_parts),
        "user_prompt": "\n\n".join(user_parts),
        "version": "v1",
        "source": SOURCE_PROMPT,
        "pulled_at": date.today().isoformat(),
        "input_variables": list(getattr(prompt, "input_variables", [])),
        "tags": ["bug-analysis", "user-story", "product-management"],
    }
    if others:
        data["other_messages"] = others
    return data


def pull_prompts_from_langsmith() -> bool:
    """Faz pull do prompt semente e salva em prompts/bug_to_user_story_v1.yml."""
    client = Client()

    print(f"Puxando prompt: {SOURCE_PROMPT}")
    try:
        prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)
    except Exception as e:
        print(f"❌ Erro ao fazer pull de '{SOURCE_PROMPT}': {e}")
        print("   Verifique LANGSMITH_API_KEY no .env e sua conexão com a internet.")
        return False

    data = {PROMPT_KEY: prompt_to_dict(prompt)}

    if not save_yaml(data, str(OUTPUT_PATH)):
        return False

    print(f"   ✓ {len(prompt.messages)} mensagem(ns) extraída(s)")
    print(f"   ✓ Variáveis: {', '.join(prompt.input_variables) or '(nenhuma)'}")
    print(f"   ✓ Salvo em: {OUTPUT_PATH.relative_to(Path.cwd()) if OUTPUT_PATH.is_relative_to(Path.cwd()) else OUTPUT_PATH}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    if not pull_prompts_from_langsmith():
        return 1

    print("\n✅ Pull concluído. Próximo passo: otimizar em prompts/bug_to_user_story_v2.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
