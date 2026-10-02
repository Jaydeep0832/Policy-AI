import json
import logging
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from groq import Groq
import google.generativeai as genai
from langsmith import traceable

from app.config import GROQ_API_KEY, GEMINI_API_KEY
from app.models import CitedChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the official Indian Institute of Management Ahmedabad (IIMA) Internal Policy AI Assistant.
Your objective is to answer employee questions strictly and exclusively using the provided policy excerpts.

LEGAL & POLICY PRECEDENCE HIERARCHY:
1. Statutory Regulations: "IIMA Gazetted Regulations (IIM Act 2017)" carries the highest legal authority.
2. Master Institutional Policy: "IIMA HR Policy Manual (Staff) 2026" (v2026.1) is the authoritative baseline for all staff rules.
3. Departmental Addenda & Memos: E.g., "Executive Special Leave and Encashment Addendum" applies specifically to executive cadres as an exception or modification.
4. Operational Guidelines: "Employee Workplace Policy Manual" or Website Terms.

CRITICAL RULES:
1. STRICT GROUNDING: Answer ONLY based on the facts explicitly mentioned in the context. Never hallucinate, extrapolate, or use outside knowledge.
2. VERSION PRECEDENCE: Always apply the 2026 Staff HR Manual rules. The 2024 manual is superseded.
3. CONFLICT HANDLING: If two active policies contain contradictory provisions or different limits on the same subject (e.g., General Staff Manual 300 days vs Executive Addendum 180 days):
   - Identify both provisions clearly.
   - Explain the difference and cite both sources.
   - Apply the precedence hierarchy: explain which policy governs (e.g. general staff vs executive cadre exception, or statutory vs departmental).
   - Set status to "policy_conflict" and has_conflict to true. Do NOT use "needs_clarification" when both provisions are present in the context; explain the dual rules and set status to "policy_conflict".
4. INSUFFICIENT INFORMATION: If the provided policy excerpts do not contain enough facts to answer the question, do NOT invent an answer. Set status to "insufficient_information" and state clearly that the available documents do not contain enough information.
5. AMBIGUOUS QUERIES: Only if the question is genuinely ambiguous and cannot be answered by comparing the provided documents, set status to "needs_clarification" and ask a concise clarifying question.
6. CITATIONS: Every claim must be supported by citations. In the "citations" array, provide the exact "chunk_id" (found in the [DOC: ... | CHUNK_ID: ...] header) and the verbatim "quoted_snippet" from that chunk.

You MUST respond in valid JSON conforming to this schema:
{
  "status": "answered" | "policy_conflict" | "needs_clarification" | "insufficient_information",
  "answer": "string",
  "has_conflict": boolean,
  "conflict_analysis": "string or null",
  "citations": [
    {
      "chunk_id": "string",
      "quoted_snippet": "string"
    }
  ]
}
"""

class LLMRouter:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API_KEY, max_retries=0) if GROQ_API_KEY else None
        self._call_count = 0
        self.total_calls = 0
        self.failover_count = 0
        self.model_stats = {
            "openai/gpt-oss-20b": 0,
            "qwen/qwen3.8-27b": 0,
            "openai/gpt-oss-120b": 0,
            "gemini-1.5-flash": 0
        }
        self.failover_history: List[Dict[str, Any]] = []

        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.gemini_model = None

    def get_failover_status(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry on model usage, failover events, and cascade health."""
        return {
            "total_calls": self.total_calls,
            "failover_count": self.failover_count,
            "model_usage": self.model_stats,
            "configured_cascade": [
                {"tier": 1, "model": "openai/gpt-oss-20b", "provider": "Groq", "role": "Primary MoE Fast Reasoner", "rate_budget": "8k TPM Free Tier"},
                {"tier": 2, "model": "qwen/qwen3.8-27b", "provider": "Groq", "role": "Secondary Dense Reasoner (Quota Balancer)", "rate_budget": "8k TPM Free Tier"},
                {"tier": 3, "model": "openai/gpt-oss-120b", "provider": "Groq", "role": "Tertiary Flagship Reasoner (Fallback)", "rate_budget": "8k TPM Free Tier"},
                {"tier": 4, "model": "gemini-1.5-flash", "provider": "Google Gemini", "role": "External Failover Provider", "rate_budget": "15 RPM Free Tier"}
            ],
            "failover_history": self.failover_history[-15:],
            "active_strategy": "Round-robin load balancing between 20B and 27B + 2-attempt backoff (8.0s cooldown) + cross-provider Gemini failover"
        }

    @traceable(name="llm_structured_synthesis", run_type="llm")
    def synthesize_answer(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Synthesizes structured response with round-robin load balancing and instant failover."""
        llm_start = time.time()
        context_blocks = []
        for c in retrieved_chunks:
            context_blocks.append(c["text"])
        formatted_context = "\n\n---\n\n".join(context_blocks)

        user_content = f"CONTEXT:\n{formatted_context}\n\nQUESTION: {question}\n\nProvide your response in JSON according to the instructions:"

        # Alternate primary model to distribute token quotas across independent buckets
        self._call_count += 1
        if self._call_count % 2 == 1:
            groq_models = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
        else:
            groq_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]

        failover_trail: List[Dict[str, Any]] = []

        if self.groq_client:
            for attempt in range(2):
                for model_name in groq_models:
                    try:
                        response = self.groq_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_content}
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.1,
                            max_tokens=1500
                        )
                        raw_text = response.choices[0].message.content
                        parsed = json.loads(raw_text)

                        # Update telemetry
                        self.total_calls += 1
                        self.model_stats[model_name] = self.model_stats.get(model_name, 0) + 1
                        elapsed_ms = round((time.time() - llm_start) * 1000, 1)

                        if failover_trail:
                            self.failover_count += 1
                            self.failover_history.append({
                                "timestamp": time.strftime("%H:%M:%S"),
                                "question": question[:60] + "..." if len(question) > 60 else question,
                                "failed_attempts": len(failover_trail),
                                "trail": failover_trail,
                                "succeeded_with": model_name,
                                "latency_ms": elapsed_ms
                            })

                        parsed["_llm_meta"] = {
                            "model_used": model_name,
                            "provider": "Groq",
                            "failover_occurred": bool(failover_trail),
                            "failover_trail": failover_trail,
                            "llm_latency_ms": elapsed_ms
                        }
                        return parsed
                    except Exception as e:
                        err_str = str(e)
                        logger.warning(f"Groq model {model_name} (attempt {attempt+1}) failed: {err_str}. Trying next model...")
                        failover_trail.append({
                            "model": model_name,
                            "attempt": attempt + 1,
                            "error": err_str[:120]
                        })
                if attempt == 0:
                    time.sleep(8.0)

        # Fallback: Google Gemini
        if self.gemini_model:
            try:
                prompt = f"{SYSTEM_PROMPT}\n\n{user_content}"
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        max_output_tokens=1500
                    )
                )
                parsed = json.loads(response.text)
                self.total_calls += 1
                self.failover_count += 1
                self.model_stats["gemini-1.5-flash"] = self.model_stats.get("gemini-1.5-flash", 0) + 1
                elapsed_ms = round((time.time() - llm_start) * 1000, 1)

                self.failover_history.append({
                    "timestamp": time.strftime("%H:%M:%S"),
                    "question": question[:60] + "..." if len(question) > 60 else question,
                    "failed_attempts": len(failover_trail),
                    "trail": failover_trail,
                    "succeeded_with": "gemini-1.5-flash",
                    "latency_ms": elapsed_ms
                })

                parsed["_llm_meta"] = {
                    "model_used": "gemini-1.5-flash",
                    "provider": "Google Gemini",
                    "failover_occurred": True,
                    "failover_trail": failover_trail,
                    "llm_latency_ms": elapsed_ms
                }
                return parsed
            except Exception as e:
                logger.error(f"Gemini fallback failed: {e}")
                failover_trail.append({
                    "model": "gemini-1.5-flash",
                    "attempt": 1,
                    "error": str(e)[:120]
                })

        # If all providers fail, return graceful fallback
        elapsed_ms = round((time.time() - llm_start) * 1000, 1)
        return {
            "status": "insufficient_information",
            "answer": "All inference providers are currently unavailable or rate limited. Please try again in a moment.",
            "has_conflict": False,
            "conflict_analysis": None,
            "citations": [],
            "_llm_meta": {
                "model_used": "None (All Failed)",
                "provider": "None",
                "failover_occurred": True,
                "failover_trail": failover_trail,
                "llm_latency_ms": elapsed_ms
            }
        }
