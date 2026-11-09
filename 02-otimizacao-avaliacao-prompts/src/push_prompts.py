"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub ({USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2)
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

`USERNAME_LANGSMITH_HUB` precisa ser o seu handle público do Hub. Se você ainda
não tem um handle, veja as instruções no .env.example / README.md.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"
REQUIRED_INPUT_VARIABLE = "bug_report"


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate (system + user) a partir dos dados do YAML."""
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def build_readme(prompt_data: dict) -> str:
    """Gera o README exibido na página do prompt no Hub."""
    techniques = prompt_data.get("techniques_applied", [])
    lines = [
        f"# {PROMPT_KEY}",
        "",
        prompt_data.get("description", "").strip(),
        "",
        f"- Versão: {prompt_data.get('version', '')}",
        f"- Variável de entrada: `{{{REQUIRED_INPUT_VARIABLE}}}`",
        "",
        "## Técnicas aplicadas",
        "",
    ]
    lines += [f"- {t}" for t in techniques]
    return "\n".join(lines) + "\n"


def build_tags(prompt_data: dict) -> list:
    """Combina as tags do YAML com as técnicas aplicadas (sem duplicatas)."""
    tags = list(prompt_data.get("tags", []))
    tags.append(prompt_data.get("version", "v2"))
    for technique in prompt_data.get("techniques_applied", []):
        slug = technique.lower().replace(" ", "-").replace("(", "").replace(")", "")
        tags.append(f"technique-{slug}")
    return list(dict.fromkeys(t for t in tags if t))


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    client = Client()
    prompt = build_chat_prompt(prompt_data)

    print(f"Fazendo push de: {prompt_name}")
    try:
        url = client.push_prompt(
            prompt_name,
            object=prompt,
            is_public=True,
            description=prompt_data.get("description", "").strip(),
            readme=build_readme(prompt_data),
            tags=build_tags(prompt_data),
        )
    except Exception as e:
        message = str(e).lower()
        if "nothing to commit" in message or "409" in message:
            print("   ℹ️  Nenhuma alteração desde o último push (commit idêntico já existe).")
            return True
        print(f"❌ Erro ao fazer push: {e}")
        if "handle" in message or "403" in message or "404" in message:
            print("   Confira se USERNAME_LANGSMITH_HUB é o seu handle público do Hub")
            print("   (ele é criado ao tornar um prompt público pela primeira vez).")
        return False

    print("   ✓ Push realizado (público)")
    print(f"   ✓ Tags: {', '.join(build_tags(prompt_data))}")
    print(f"   ✓ {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    _, errors = validate_prompt_structure(prompt_data)
    errors = list(errors)

    user_prompt = (prompt_data.get("user_prompt") or "").strip()
    if not user_prompt:
        errors.append("user_prompt está vazio")
    elif f"{{{REQUIRED_INPUT_VARIABLE}}}" not in user_prompt:
        errors.append(f"user_prompt precisa conter a variável {{{REQUIRED_INPUT_VARIABLE}}}")

    if f"{{{REQUIRED_INPUT_VARIABLE}}}" in prompt_data.get("system_prompt", ""):
        errors.append(f"{{{REQUIRED_INPUT_VARIABLE}}} deve ficar só no user_prompt, não no system_prompt")

    # Garante que o template é montável e que a única variável é {bug_report}
    if not errors:
        try:
            variables = set(build_chat_prompt(prompt_data).input_variables)
            if variables != {REQUIRED_INPUT_VARIABLE}:
                errors.append(
                    f"Variáveis do template devem ser só {{{REQUIRED_INPUT_VARIABLE}}}, "
                    f"encontradas: {sorted(variables)} (escape chaves literais com {{{{ }}}})"
                )
        except Exception as e:
            errors.append(f"Template inválido: {e}")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS PARA O LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not data or PROMPT_KEY not in data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_PATH}")
        return 1

    prompt_data = data[PROMPT_KEY]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("✓ Prompt validado")

    username = os.getenv("USERNAME_LANGSMITH_HUB").strip()
    prompt_name = f"{username}/{PROMPT_KEY}"

    if not push_prompt_to_langsmith(prompt_name, prompt_data):
        return 1

    print("\n✅ Push concluído. Próximo passo: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
