# Template do Relatório de Auditoria (Fase 2)

O relatório é impresso no terminal **e** salvo em Markdown. Siga a estrutura abaixo sem remover
seções. Use os nomes de campo em inglês (`File`, `Description`, `Impact`, `Recommendation`) para
manter o formato padronizado entre projetos; o conteúdo descritivo pode ser em português.

## Regras

1. Findings ordenados por severidade: **CRITICAL → HIGH → MEDIUM → LOW**.
2. Numere os findings sequencialmente (`F-01`, `F-02`, ...) após ordenar.
3. `File:` sempre com caminho relativo à raiz do projeto + linha (`app.py:7`) ou intervalo
   (`models.py:24-41`). Várias ocorrências: separe por vírgula (`a.py:10, b.py:22-30`).
4. Cada finding cita o ID do catálogo (`AP-xx`) e a transformação (`Playbook P-xx`).
5. O `Summary` deve bater com a contagem real de findings.
6. A seção `Deprecated APIs` é obrigatória — liste as ocorrências ou "none detected" com as versões verificadas.
7. Termine **sempre** com a linha de confirmação.
8. No arquivo salvo, inclua antes do relatório o bloco `PHASE 1: PROJECT ANALYSIS` (contexto
   para quem revisa o relatório fora do terminal), dentro de um `<details>`.

## Estrutura

````markdown
```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório>
Stack:   <Linguagem> + <Framework versão>
Files:   <n> analyzed | ~<loc> lines of code
Date:    <AAAA-MM-DD>
```

## Summary

| Severity | Count |
|---|---|
| CRITICAL | <n> |
| HIGH | <n> |
| MEDIUM | <n> |
| LOW | <n> |
| **Total** | **<n>** |

## Findings

### F-01 [CRITICAL] <Título> (AP-xx)
- **File:** `<arquivo>:<linha(s)>`
- **Description:** <o que está errado, citando o trecho/valor>
- **Impact:** <consequência concreta: segurança, manutenção, performance>
- **Recommendation:** <correção> → Playbook P-xx

### F-02 [HIGH] ...

## Deprecated APIs

| File:Line | Deprecated API | Modern replacement |
|---|---|---|
| `<arquivo>:<linha>` | `<api>` | `<substituto>` |

(ou: `none detected — verificado contra <stack/versões>`)

## Proposed target structure

```
<árvore MVC proposta para a Fase 3 (ver mvc-guidelines.md)>
```

```
================================
Total: <n> findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
````

## Exemplo de finding bem escrito

```markdown
### F-02 [CRITICAL] SQL Injection em todas as queries (AP-02)
- **File:** `models.py:28, 47-50, 57-61, 109-111`
- **Description:** Queries montadas por concatenação de strings com dados do request, ex.:
  `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
- **Impact:** Bypass de login com `admin@loja.com' --`; leitura/alteração arbitrária do banco.
- **Recommendation:** Usar placeholders do driver (`?`) em todas as queries → Playbook P-02
```

## Exemplo de finding ruim (não faça)

```markdown
### [HIGH] Código ruim
File: vários arquivos
Description: o código poderia ser melhor.
```
(sem linha exata, sem impacto, sem ID do catálogo, sem recomendação acionável)
