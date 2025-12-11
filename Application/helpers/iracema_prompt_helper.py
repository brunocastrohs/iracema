# Application/helpers/iracema_prompt_helper.py

from typing import List, Dict, Any

TABLE_NAME = 'public."1201_ce_zeec_zoneamento_p_litora_2021_pol"'


SCHEMA_DESCRIPTION = f"""
Você é um assistente especializado na base de dados ZEEC do litoral do Ceará.

Trabalhe EXCLUSIVAMENTE com a tabela {TABLE_NAME} no PostgreSQL.

Esquema da tabela:

- gid        (integer, PRIMARY KEY): identificador interno da feição.
- id         (numeric): identificador da zona/subzona no estudo ZEEC.
- zonas      (varchar(254)): nome da zona de zoneamento ecológico-econômico.
- sub_zonas  (varchar(254)): nome da subzona associada.
- letra_subz (varchar(254)): letra/código da subzona.
- perimet_km (numeric): perímetro da feição em quilômetros.
- area_km2   (numeric): área da feição em quilômetros quadrados.
- geom       (geometry(MultiPolygon, 4674)): geometria da feição.
  ATENÇÃO: no MVP, NÃO utilize a coluna geom em nenhuma consulta.

Regras importantes:

1. Gere apenas comandos SQL do tipo SELECT (e agregações).
2. NUNCA utilize INSERT, UPDATE, DELETE, DROP, ALTER ou comandos de definição de schema.
3. Sempre referencie explicitamente o nome da tabela: {TABLE_NAME}.
4. Prefira filtros em colunas textuais usando ILIKE quando fizer sentido.
5. Use aliases amigáveis (por exemplo: zona, subzona, area_total_km2).
6. Respeite um LIMIT se o usuário não pedir agregações (por exemplo LIMIT {{top_k}}).
"""


def build_sql_generation_prompt(question: str, top_k: int = 20) -> str:
    """
    Prompt para a PRIMEIRA chamada ao LLM (geração de SQL).
    O modelo deve retornar APENAS um comando SQL SELECT válido.
    """
    return f"""{SCHEMA_DESCRIPTION}

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

    # cria uma tabela simples em texto para dar contexto ao LLM
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

    return f"""
Você recebeu o resultado de uma consulta SQL executada sobre a tabela ZEEC.

Pergunta original do usuário:
\"\"\"{question}\"\"\"

SQL executado:
```sql
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