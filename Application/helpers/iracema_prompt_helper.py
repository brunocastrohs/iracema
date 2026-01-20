from typing import List, Dict, Any, Optional

def build_sql_generation_prompt(
    schema_description: str,
    question: str,
    top_k: int = 20,
) -> str:
    """
    Prompt para a PRIMEIRA chamada ao LLM (geração de SQL).

    Agora que `schema_description` já vem no template sqlcoder (PT-BR),
    o único trabalho desta função é substituir o placeholder
    {PERGUNTA_DO_USUARIO} pelo texto de `question`.

    Observação: `top_k` fica aqui por compatibilidade de assinatura, mas
    o LIMIT já deve estar embutido no schema_description (gerado pelo build_prompt_inicial).
    """
    placeholder = "{PERGUNTA_DO_USUARIO}"
    if placeholder in schema_description:
        return schema_description.replace(placeholder, question)
    # fallback caso o template venha com outro placeholder ou já esteja preenchido
    return schema_description



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

    return f"""Você recebeu o resultado de uma consulta SQL executada sobre o dataset escolhido. SQL executado: {sql_executed}
            
            Prévia das primeiras linhas (máximo {max_preview}): {table_text}

            Explique o resultado em uma frase."""
