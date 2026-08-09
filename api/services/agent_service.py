"""
api/services/agent_service.py – Gemini Tool-Use 기반 자율 공시 에이전트 서비스

Gemini LLM이 스스로 백엔드 검증 도구(list_dsd_templates, read_dsd_template, validate_against_template 등)를 
호출하며 비정형 공시 데이터를 2차 규격까지 검증 및 패키징하는 자율 에이전트 루프 모듈입니다.
"""

import logging
from typing import Any, Callable

import google.generativeai as genai
from api.config import get_settings
from api.services.dsd_service import (
    build_dsd_in_memory,
    find_empty_template_by_name,
    get_templates_root,
    list_templates,
    read_template,
    validate_against_template,
)

logger = logging.getLogger(__name__)


class DisclosureAgentService:
    """Gemini Tool-Use 공시 자율 작성 에이전트 모듈"""

    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.google_api_key)
        self.model_name = self.settings.gemini_model

    def get_registered_tools(self) -> list[Callable]:
        """Gemini 에이전트에 공급할 백엔드 툴 함수 화이트리스트"""

        def tool_list_dsd_templates() -> list[str]:
            """사용 가능한 .dsd 템플릿 목록을 반환합니다."""
            return [t.name for t in list_templates()]

        def tool_read_dsd_template(template_name: str) -> dict[str, str]:
            """특정 템플릿의 contents.xml 및 meta.xml 내용을 파싱해 읽어옵니다."""
            path = find_empty_template_by_name(template_name)
            if not path:
                return {"error": f"템플릿 '{template_name}'을 찾을 수 없습니다."}
            return read_template(path)

        def tool_validate_dsd_xml(contents_xml: str, template_name: str) -> list[str]:
            """DART XML 태그 및 행 보존 규칙을 2차 사전 검증하고 오류 목록을 반환합니다."""
            path = find_empty_template_by_name(template_name)
            if not path:
                return [f"템플릿 '{template_name}' 부재"]
            empty_tpl = read_template(path)
            return validate_against_template(contents_xml, empty_tpl["contents_xml"])

        return [tool_list_dsd_templates, tool_read_dsd_template, tool_validate_dsd_xml]

    async def run_agent_loop(self, user_prompt: str, document_text: str = "") -> dict[str, Any]:
        """
        사용자 요청 및 비정형 문서 텍스트를 전달받아 Gemini Tool-Use 루프를 수행합니다.

        Args:
            user_prompt: 사용자의 지시사항 (예: "기술이전 계약서로 주요사항보고서 초안 작성해줘")
            document_text: 원본 비정형 문서 텍스트

        Returns:
            {"agent_response": str, "tool_calls": list}
        """
        tools = self.get_registered_tools()
        system_instruction = (
            "당신은 대한민국 DART/KIND 공시 작성 전용 전문 AI 에이전트입니다.\n"
            "비정형 문서와 지시사항을 해석하여 DART 규격에 맞게 XML 필드를 채우고,\n"
            "tool_validate_dsd_xml 도구를 사용해 검증 오류를 스스로 수정한 후 결과를 응답하세요.\n"
            "응답은 반드시 한국어로 작성하세요."
        )

        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                tools=tools,
                system_instruction=system_instruction,
            )
            chat = model.start_chat(enable_automatic_function_calling=True)

            full_prompt = f"{user_prompt}\n\n[원본 공시 자료]\n{document_text}" if document_text else user_prompt
            response = chat.send_message(full_prompt)

            logger.info("Gemini Agent 루프 수행 완료 (모델: %s)", self.model_name)
            return {
                "status": "success",
                "agent_response": response.text,
                "history_length": len(chat.history),
            }

        except Exception as exc:
            logger.error("Gemini Agent 루프 실행 중 오류 발생: %s", exc)
            return {
                "status": "error",
                "message": f"에이전트 실행 실패: {exc}",
            }
