"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    data = load_prompts(PROMPT_FILE)
    assert data and PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE}"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt_data):
    return prompt_data.get("system_prompt") or ""


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data
        assert isinstance(prompt_data["system_prompt"], str)
        assert prompt_data["system_prompt"].strip()

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é um[a]? ", system_prompt), "Persona não definida com 'Você é um(a) ...'"
        assert re.search(r"Product Manager|Product Owner|Analista", system_prompt, re.IGNORECASE)

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        assert re.search(r"markdown|user story", system_prompt, re.IGNORECASE)
        # Template padrão: Como um ... eu quero ... para que ...
        for part in ("Como um", "eu quero", "para que"):
            assert part in system_prompt, f"Template de User Story sem '{part}'"
        # Critérios de aceitação no formato Dado/Quando/Então
        for part in ("Critérios de Aceitação", "Dado que", "Quando", "Então"):
            assert part in system_prompt, f"Formato de critérios sem '{part}'"

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        examples = re.findall(r"Exemplo \d", system_prompt)
        inputs = system_prompt.count("Relato de bug:")
        outputs = system_prompt.count("Resposta:")
        assert len(examples) >= 2, "Few-shot exige pelo menos 2 exemplos"
        assert inputs >= 2 and outputs >= 2, "Cada exemplo precisa de entrada e saída"
        assert inputs == outputs, "Número de entradas e saídas dos exemplos não confere"

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        full_text = yaml.safe_dump(prompt_data, allow_unicode=True)
        assert "[TODO]" not in full_text
        assert not re.search(r"\bTODO\b", full_text)
        # O validador oficial também não pode acusar TODO no system_prompt
        _, errors = validate_prompt_structure(prompt_data)
        assert not any("TODO" in e for e in errors), errors

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert any("few-shot" in t.lower() for t in techniques), "Few-shot é obrigatório"


class TestPromptTemplate:
    """Testes extras: o template precisa ser montável e usar só {bug_report}."""

    def test_structure_is_valid(self, prompt_data):
        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, errors

    def test_bug_report_only_in_user_prompt(self, prompt_data):
        assert "{bug_report}" in prompt_data["user_prompt"]
        assert "{bug_report}" not in prompt_data["system_prompt"]

    def test_template_variables(self, prompt_data):
        langchain_prompts = pytest.importorskip("langchain_core.prompts")
        template = langchain_prompts.ChatPromptTemplate.from_messages([
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ])
        assert set(template.input_variables) == {"bug_report"}
        rendered = template.format_messages(bug_report="Botão X não funciona.")
        assert "Botão X não funciona." in rendered[1].content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
