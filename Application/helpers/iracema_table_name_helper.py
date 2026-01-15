from typing import Optional


def build_table_fqn(table_identifier: str, schema: str = "zcm") -> str:
    """
    Constrói o nome totalmente qualificado com quote seguro.

    Ex:
    - input: 1201_ce_zeec_zoneamento_p_litora_2021_pol
    - output: public."1201_ce_zeec_zoneamento_p_litora_2021_pol"
    """
    if not table_identifier or not table_identifier.strip():
        raise ValueError("table_identifier vazio.")

    t = table_identifier.strip()

    # se já vier qualificado tipo public."x" ou public.x, normaliza
    if "." in t:
        # o serviço pode decidir se permite schema externo; por ora, mantenha o input
        return t

    return f'{schema}."{t}"'
