from typing import List
from Domain.datasource_model import DataSource


def format_candidates_br(candidates: List[DataSource]) -> str:
    """
    Gera um texto curto listando candidatos.
    """
    lines = []
    for ds in candidates:
        lines.append(
            f"- ID {ds.id}: {ds.titulo_tabela} (tabela: {ds.identificador_tabela})"
        )
    return "\n".join(lines)


def build_start_need_more_info_message(candidates: List[DataSource]) -> str:
    return (
        "Encontrei mais de uma camada/tabela que pode corresponder ao que você quer.\n\n"
        "Escolha uma opção informando o ID (ex.: `id 12`) ou diga mais detalhes do que você busca:\n\n"
        f"{format_candidates_br(candidates)}"
    )


def build_start_resolved_message(selected: DataSource) -> str:
    return (
        "Contexto definido ✅\n\n"
        f"Vou trabalhar com: **{selected.titulo_tabela}**\n"
        f"Tabela: `{selected.identificador_tabela}`\n\n"
        "Agora você já pode fazer perguntas no endpoint **/ask** usando este conversation_id."
    )


def build_start_no_match_message() -> str:
    return (
        "Não encontrei nenhuma camada/tabela correspondente ao que você descreveu.\n"
        "Tente usar palavras-chave do tema (ex.: 'ZEEC', 'zoneamento', 'saneamento', 'distritos') "
        "ou peça para eu listar opções."
    )
