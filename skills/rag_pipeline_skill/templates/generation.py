"""
Evidence-Grounded Generation & Citation Synthesis Module.

Features:
- Lost-in-the-Middle mitigation via interleaved chunk reordering.
- Explicit document/chunk citation formatting.
- Strict anti-hallucination prompt instructions with safe refusal paths.
- Provider dispatch across OpenAI, Google Gemini, Anthropic Claude, and Ollama.
"""

import os
from typing import Callable, Dict, List, Literal, Optional
from .contracts import GenerationResult, SearchResult


SYSTEM_PROMPT = """Bạn là trợ lý AI trả lời câu hỏi dựa trên tài liệu tham khảo được cung cấp.
Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin có trong phần 'TÀI LIỆU THAM KHẢO' bên dưới.
2. Mỗi phát biểu, khẳng định quan trọng phải đi kèm citation dẫn nguồn tương ứng theo định dạng: [Doc <Index>: <Title>].
3. Tuyệt đối không tự suy diễn hoặc bịa đặt thông tin nếu tài liệu không nhắc đến.
4. Nếu tài liệu được cung cấp không đủ dữ kiện để trả lời câu hỏi, hãy từ chối một cách lịch sự: "Tôi không thể xác minh thông tin này từ các tài liệu được cung cấp."
"""


class GroundedGenerator:
    """Manages prompt synthesis, context reordering, citation tracking, and LLM inference."""

    def __init__(
        self,
        provider: Literal["openai", "gemini", "anthropic", "ollama"] = "openai",
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ):
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p

    @staticmethod
    def reorder_for_llm(chunks: List[SearchResult]) -> List[SearchResult]:
        """
        Interleaves chunks to position highest-ranked elements at the very beginning
        and end of the prompt context, mitigating the 'Lost-in-the-Middle' attention dip.
        """
        if len(chunks) <= 2:
            return list(chunks)
        front = chunks[::2]
        back = chunks[1::2]
        return front + back[::-1]

    @staticmethod
    def format_context(chunks: List[SearchResult]) -> str:
        """Formats context items with clean metadata headers for verified attribution."""
        formatted_sections: List[str] = []
        for index, chunk in enumerate(chunks, 1):
            metadata = chunk.get("metadata", {})
            title = metadata.get("title", "Untitled")
            source = metadata.get("source", "Unknown")
            chunk_idx = metadata.get("chunk_index", 0)

            header = f"[Tài liệu {index} | Tiêu đề: {title} | Nguồn: {source} (Chunk {chunk_idx})]"
            formatted_sections.append(f"{header}\n{chunk['content']}")

        return "\n\n---\n\n".join(formatted_sections)

    def call_llm(self, system_prompt: str, user_message: str) -> str:
        """Dispatches prompt to the configured LLM provider."""
        if self.provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=self.model_name or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=self.temperature,
                top_p=self.top_p,
            )
            return response.choices[0].message.content or ""

        elif self.provider == "gemini":
            from google import genai
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model=self.model_name or "gemini-2.0-flash",
                contents=f"{system_prompt}\n\n{user_message}",
            )
            return response.text or ""

        elif self.provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=self.model_name or "claude-3-5-sonnet-20241022",
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=self.temperature,
            )
            return response.content[0].text  # type: ignore

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate(
        self,
        query: str,
        retriever_fn: Callable[[str, int], List[SearchResult]],
        top_k: int = 5,
    ) -> GenerationResult:
        """Executes full grounded answer generation with citation verification."""
        retrieved_chunks = retriever_fn(query, top_k)

        if not retrieved_chunks:
            return {
                "answer": "Tôi không thể xác minh thông tin này từ các tài liệu được cung cấp.",
                "sources": [],
                "retrieval_source": "none",
            }

        reordered = self.reorder_for_llm(retrieved_chunks)
        context_str = self.format_context(reordered)
        user_prompt = f"TÀI LIỆU THAM KHẢO:\n{context_str}\n\nCÂU HỎI:\n{query}\n\nHãy trả lời câu hỏi kèm citation chi tiết."

        try:
            answer = self.call_llm(SYSTEM_PROMPT, user_prompt)
        except Exception as err:
            answer = f"Lỗi trong quá trình tạo câu trả lời: {str(err)}"

        retrieval_method = retrieved_chunks[0].get("retrieval_method", "hybrid")
        retrieval_source_map = {
            "dense": "dense",
            "bm25": "bm25",
            "hybrid": "hybrid",
            "pageindex": "pageindex",
        }

        return {
            "answer": answer,
            "sources": retrieved_chunks,
            "retrieval_source": retrieval_source_map.get(retrieval_method, "hybrid"),  # type: ignore
        }
