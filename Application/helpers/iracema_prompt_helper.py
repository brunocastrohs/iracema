from typing import List, Dict, Any, Optional


def build_sql_generation_prompt(
    schema_description: str,
    question: str,
    top_k: int = 20,
) -> str:
    """
    Prompt para a PRIMEIRA chamada ao LLM (geração de SQL).
    O modelo deve retornar APENAS um comando SQL SELECT válido.
    """
    return f"""{schema_description}

Sua tarefa agora é: dada uma pergunta em português do usuário sobre os dados desta tabela,
gerar UM ÚNICO comando SQL SELECT que responda à pergunta.

Pergunta do usuário:
\"\"\"{question}\"\"\"

Requisitos adicionais:

- Não adicione comentários no SQL.
- Não quebre em múltiplos comandos.
- Se a consulta não fizer sentido, gere um SELECT com WHERE 1 = 0.
- Se a consulta não envolver agregações, utilize LIMIT {top_k}.
- NÃO utilize a coluna geom em nenhuma condição, filtro ou retorno.

Retorne apenas o SQL, nada mais.
"""


def build_explanation_prompt(
    schema_description: str,
    question: str,
    sql_executed: str,
    rows: List[Dict[str, Any]],
    rowcount: int,
) -> str:
    """
    Prompt para a SEGUNDA chamada ao LLM (explicação do resultado SQL).
    """
    max_preview = min(len(rows), 20)
    preview_rows = rows[:max_preview]

    if preview_rows:
        header = list(preview_rows[0].keys())
        lines = [
            " | ".join(str(h) for h in header),
            "-" * 40,
        ]
        for r in preview_rows:
            lines.append(" | ".join(str(r.get(h, "")) for h in header))
        table_text = "\n".join(lines)
    else:
        table_text = "(sem linhas de exemplo)"

    return f"""{schema_description}

Você recebeu o resultado de uma consulta SQL executada sobre o dataset escolhido.

Pergunta original do usuário:
\"\"\"{question}\"\"\"

SQL executado:

{sql_executed}
Quantidade de linhas retornadas: {rowcount}

Prévia das primeiras linhas (máximo {max_preview}):
{table_text}

Agora, produza uma resposta clara e objetiva em português, explicando o significado desses resultados.

NÃO repita o SQL.

Se houver agregações (SUM, AVG, etc.), explique o que elas significam.

Se não houver linhas, informe que não foram encontrados registros compatíveis.

Utilize unidades como km² e km conforme apropriado.
"""
