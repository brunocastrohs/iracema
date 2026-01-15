from typing import Optional, List, Dict, Any

from Domain.interfaces.i_iracema_conversation_repository import IIracemaConversationRepository
from Domain.interfaces.i_iracema_message_repository import IIracemaMessageRepository
from Domain.interfaces.i_iracema_datasource_repository import IIracemaDataSourceRepository
from Domain.interfaces.i_iracema_conversation_context_repository import (
    IIracemaConversationContextRepository,
)

from Domain.iracema_enums import MessageRoleEnum, ConversationContextStatusEnum

from Data.db_context import DbContext

from Application.interfaces.i_iracema_start_service import IIracemaStartService
from Application.dto.iracema_start_dto import (
    IracemaStartRequestDto,
    IracemaStartResponseDto,
)
from Application.mappings.iracema_mappings import build_start_response_dto

from Application.helpers.iracema_start_intent_helper import detect_start_intent
from Application.helpers.iracema_start_response_helper import (
    build_start_need_more_info_message,
    build_start_resolved_message,
    build_start_no_match_message,
)


class IracemaStartService(IIracemaStartService):
    def __init__(
        self,
        db_context: DbContext,
        conversation_repo: IIracemaConversationRepository,
        message_repo: IIracemaMessageRepository,
        datasource_repo: IIracemaDataSourceRepository,
        context_repo: IIracemaConversationContextRepository,
    ) -> None:
        self._db_context = db_context
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._datasource_repo = datasource_repo
        self._context_repo = context_repo

    def start(self, request: IracemaStartRequestDto) -> IracemaStartResponseDto:
        session = self._db_context.create_session()

        user_text = request.message.strip()
        error_message: Optional[str] = None

        conversation = None
        user_message = None
        assistant_message = None

        try:
            # 1) conversa
            conversation = self._conversation_repo.get_or_create(
                session=session,
                conversation_id=request.conversation_id,
                title=user_text[:120] if user_text else None,
            )

            # 2) contexto
            ctx = self._context_repo.ensure_exists(session=session, conversation_id=conversation.id)

            # 3) registrar msg do usuário
            user_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.USER,
                content=user_text,
            )
            session.flush()

            intent = detect_start_intent(user_text)

            # 4) reset/trocar camada
            if intent.kind == "change":
                ctx = self._context_repo.clear_selection(session=session, conversation_id=conversation.id)
                assistant_text = (
                    "Certo — vamos redefinir o contexto.\n"
                    "Diga o tema/assunto da camada que você quer consultar, ou peça para eu listar opções."
                )

                assistant_message = self._message_repo.add_message(
                    session=session,
                    conversation_id=conversation.id,
                    role=MessageRoleEnum.ASSISTANT,
                    content=assistant_text,
                )
                session.flush()

                resp = build_start_response_dto(
                    conversation=conversation,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    assistant_text=assistant_text,
                    resolved=False,
                    candidates=[],
                    start_state={
                        "status": ctx.status,
                        "attempts": ctx.start_attempts,
                    },
                )
                session.close()
                return resp

            # 5) seleção direta por ID
            if intent.kind == "select_id":
                ds_id = int(intent.value)  # type: ignore
                ds = self._datasource_repo.get_by_id(session=session, datasource_id=ds_id)

                if ds is None or not ds.is_ativo:
                    assistant_text = (
                        "Não encontrei uma datasource ativa com esse ID. "
                        "Tente escolher outra opção ou descreva novamente o que você busca."
                    )
                    assistant_message = self._message_repo.add_message(
                        session=session,
                        conversation_id=conversation.id,
                        role=MessageRoleEnum.ASSISTANT,
                        content=assistant_text,
                    )
                    session.flush()

                    resp = build_start_response_dto(
                        conversation=conversation,
                        user_message=user_message,
                        assistant_message=assistant_message,
                        assistant_text=assistant_text,
                        resolved=False,
                        candidates=[],
                        start_state={"status": ctx.status},
                    )
                    session.close()
                    return resp

                # fixa contexto
                ctx = self._context_repo.set_datasource_selected(
                    session=session,
                    conversation_id=conversation.id,
                    datasource_id=ds.id,
                    table_identifier=ds.identificador_tabela,
                    prompt_inicial_snapshot=ds.prompt_inicial,
                )

                assistant_text = build_start_resolved_message(ds)
                assistant_message = self._message_repo.add_message(
                    session=session,
                    conversation_id=conversation.id,
                    role=MessageRoleEnum.ASSISTANT,
                    content=assistant_text,
                )
                session.flush()

                resp = build_start_response_dto(
                    conversation=conversation,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    assistant_text=assistant_text,
                    resolved=True,
                    table_identifier=ds.identificador_tabela,
                    datasource_id=ds.id,
                    prompt_inicial=ds.prompt_inicial,
                    reason="selected_by_id",
                    candidates=[],
                    start_state={"status": ctx.status},
                )
                session.close()
                return resp

            # 6) list/search em datasources
            if intent.kind == "list":
                candidates = self._datasource_repo.list_active(
                    session=session,
                    limit=request.max_candidates,
                    offset=0,
                )
            else:
                candidates = self._datasource_repo.search_active(
                    session=session,
                    query=intent.value or "",
                    limit=request.max_candidates,
                    offset=0,
                )

            # atualiza tentativa
            ctx.start_attempts = (ctx.start_attempts or 0) + 1
            ctx.status = ConversationContextStatusEnum.SELECTING
            self._context_repo.update(session=session, context=ctx)

            # 0 candidatos
            if not candidates:
                assistant_text = build_start_no_match_message()
                assistant_message = self._message_repo.add_message(
                    session=session,
                    conversation_id=conversation.id,
                    role=MessageRoleEnum.ASSISTANT,
                    content=assistant_text,
                )
                session.flush()

                resp = build_start_response_dto(
                    conversation=conversation,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    assistant_text=assistant_text,
                    resolved=False,
                    candidates=[],
                    start_state={"status": ctx.status, "attempts": ctx.start_attempts},
                )
                session.close()
                return resp

            # 1 candidato -> resolve automaticamente
            if len(candidates) == 1:
                ds = candidates[0]
                ctx = self._context_repo.set_datasource_selected(
                    session=session,
                    conversation_id=conversation.id,
                    datasource_id=ds.id,
                    table_identifier=ds.identificador_tabela,
                    prompt_inicial_snapshot=ds.prompt_inicial,
                )

                assistant_text = build_start_resolved_message(ds)
                assistant_message = self._message_repo.add_message(
                    session=session,
                    conversation_id=conversation.id,
                    role=MessageRoleEnum.ASSISTANT,
                    content=assistant_text,
                )
                session.flush()

                resp = build_start_response_dto(
                    conversation=conversation,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    assistant_text=assistant_text,
                    resolved=True,
                    table_identifier=ds.identificador_tabela,
                    datasource_id=ds.id,
                    prompt_inicial=ds.prompt_inicial,
                    reason="unique_match",
                    candidates=[],
                    start_state={"status": ctx.status, "attempts": ctx.start_attempts},
                )
                session.close()
                return resp

            # múltiplos candidatos -> pedir seleção
            assistant_text = build_start_need_more_info_message(candidates)
            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=assistant_text,
            )
            session.flush()

            resp = build_start_response_dto(
                conversation=conversation,
                user_message=user_message,
                assistant_message=assistant_message,
                assistant_text=assistant_text,
                resolved=False,
                candidates=candidates,
                start_state={"status": ctx.status, "attempts": ctx.start_attempts},
            )
            session.close()
            return resp

        except Exception as ex:
            error_message = str(ex)

            if conversation is None:
                conversation = self._conversation_repo.get_or_create(
                    session=session,
                    conversation_id=request.conversation_id,
                    title=user_text[:120] if user_text else None,
                )

            if user_message is None:
                user_message = self._message_repo.add_message(
                    session=session,
                    conversation_id=conversation.id,
                    role=MessageRoleEnum.USER,
                    content=user_text,
                )
                session.flush()

            assistant_text = (
                "Ocorreu um erro ao tentar resolver o contexto. "
                "Tente novamente com mais detalhes."
            )

            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=assistant_text,
            )
            session.flush()

            resp = build_start_response_dto(
                conversation=conversation,
                user_message=user_message,
                assistant_message=assistant_message,
                assistant_text=assistant_text,
                resolved=False,
                candidates=[],
                start_state={},
                error=error_message,
            )
            session.close()
            return resp
