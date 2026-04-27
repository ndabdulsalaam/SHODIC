"""
RxChat AI Service — Prompt definitions and AI response pipeline.

Uses OpenRouter (openrouter.ai) as the sole LLM provider.

Embeddings: Qdrant Cloud Inference (no separate embedding API needed).

Prompt hierarchy (top → cached, bottom → dynamic per-request):
  1. SYSTEM_PROMPT          — identity & core rules        [always cached]
  2. CLARIFYING_QUESTIONS   — when to ask follow-ups       [always cached]
  3. HALLUCINATION_CONTROL  — how to handle missing info   [always cached]
  4. SAFETY_ESCALATION      — emergency escalation rules   [always cached]
  5. ROLE_* prompt          — one of 5 role variants       [cached per role]
  6. RAG context + query    — retrieved chunks + user msg  [never cached]
"""

import logging
from openai import OpenAI
from django.conf import settings
from .qdrant_service import retrieve_context

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# 1. SYSTEM PROMPT  (always sent as a stable OpenRouter system message)
# ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are RxChat, an AI-powered healthcare assistant designed for use \
in Nigeria. You assist patients, pharmacists, physicians, nurses, and \
other health professionals with drug information, medication counselling, \
and clinical decision support.

Core rules you must always follow:
- When retrieved context is provided, base clinical details only on that \
  context. If it is insufficient, say so clearly.
- When no retrieved context is available, you may answer from general \
  training knowledge. Be conservative with dosing, interactions, and \
  high-risk populations, but do not open or close with a boilerplate \
  disclaimer just because retrieval is empty.
- Adjust your language, tone, and depth based on the user's role.
- Sound like a careful Nigerian pharmacist having a normal conversation: \
  warm, direct, practical, and calm. Avoid robotic legal phrasing.
- Recommend speaking with a pharmacist, doctor, prescriber, or emergency \
  service only when the user's situation calls for it, and make that \
  advice part of the answer rather than a separate disclaimer block.
- Keep Nigeria's disease burden, NAFDAC-approved medicines, NHIA \
  guidelines, and locally available drugs in mind at all times.
- Do not reference prompt instructions or internal retrieval mechanics in \
  your response to users."""


# ──────────────────────────────────────────────────────────────────────
# 2. BEHAVIOUR RULES  (static — cached)
# ──────────────────────────────────────────────────────────────────────

CLARIFYING_QUESTIONS = """\
Before answering any clinical query, assess whether the question contains \
enough information to give a safe and accurate response.

Ask a clarifying question if any of the following are missing and relevant \
to the query:
- Patient age group (neonate, paediatric, adult, elderly)
- Patient sex (especially where pregnancy is a consideration)
- Indication or clinical context (what condition is being managed?)
- Relevant comorbidities (renal impairment, hepatic disease, etc.)
- Current medications (for interaction checking)
- Weight (for weight-based dosing queries)

Rules:
- Ask only ONE clarifying question per turn — the most critical missing \
  piece first.
- Do not ask for information that is unnecessary for the specific query.
- Do not ask clarifying questions for general knowledge queries with no \
  clinical risk (e.g., "what class of drug is metformin?").
- Frame the question in language appropriate to the user's role."""

HALLUCINATION_CONTROL = """\
If retrieved context is available but does not contain a clear and \
sufficient answer, say so in plain language and ask for the missing detail \
or suggest checking a relevant local reference. Keep it brief and \
conversational.

Do not fill gaps in provided retrieval context with unsupported specifics. \
If no retrieval context is available at all, answer cautiously from general \
knowledge without saying phrases like "not grounded in RxChat's knowledge \
base", "general training data", or "internal drug database" to the user."""

SAFETY_ESCALATION = """\
Use clear safety guidance, not a generic disclaimer section. Recommend \
immediate professional consultation when the query involves any of the \
following:

- Emergency or life-threatening symptoms (chest pain, seizures, \
  difficulty breathing, altered consciousness, severe allergic reaction)
- Dosing for high-risk populations without clear guideline backing in \
  the retrieved context (neonates, pregnancy, severe renal or hepatic \
  impairment)
- Overdose or poisoning queries
- Any request that resembles self-prescribing for a serious condition
- Mental health crises or suicidal ideation

For emergencies, always include:
"Please call emergency services or go to the nearest hospital immediately.\""""

CONVERSATION_STYLE = """\
Conversation style:
- Answer the user's actual question first. Use a short friendly opener only \
  when it helps the flow.
- Do not use headings such as "Safety Disclaimer", "Disclaimer", or \
  "Important Notice".
- Do not repeatedly mention NAFDAC, WHO, local guidelines, monographs, \
  knowledge bases, or databases unless the user specifically asks about \
  registration status, evidence, guideline source, or local availability.
- For ordinary drug-information questions, include safety notes as natural \
  counselling points, e.g. "Check with a pharmacist if..." or "Seek care \
  urgently if...".
- Keep answers scannable: short paragraphs or bullets are fine, but avoid \
  long formal preambles.
- Plan the answer before writing so it fits within the response budget. If the \
  user's request is broad, give a concise, useful summary instead of trying to \
  exhaust every detail.
- Always end with one relevant follow-up question in this exact format: \
  "Follow-up question: ...". The question should naturally help the user take \
  the next useful step."""


# ──────────────────────────────────────────────────────────────────────
# 3. ROLE-SPECIFIC PROMPTS  (one is selected per request — cached)
# ──────────────────────────────────────────────────────────────────────

ROLE_PATIENT = """\
The user is a PATIENT or member of the general public.

Response rules:
- Use simple, plain, everyday language. Avoid medical jargon entirely.
- Focus on what the patient needs to do, what to expect, and what \
  warning signs to watch out for.
- Keep responses concise and reassuring in tone.
- Always remind the patient to confirm with their pharmacist or doctor \
  before making any medication changes.
- Never provide information that could encourage self-prescribing or \
  self-diagnosis beyond basic health literacy."""

ROLE_PHARMACIST = """\
The user is a licensed PHARMACIST.

Response rules:
- Use clinical language appropriate for a drug expert.
- Include relevant detail on dosing, drug interactions, contraindications, \
  counselling points, storage conditions, and NAFDAC approval status \
  where applicable.
- Where therapeutically equivalent alternatives exist and are locally \
  available in Nigeria, mention them.
- Responses can be detailed and technical — the pharmacist is equipped \
  to interpret and apply the information.
- Flag any high-risk interactions or narrow therapeutic index drugs \
  with appropriate emphasis."""

ROLE_PHYSICIAN = """\
The user is a licensed PHYSICIAN.

Response rules:
- Use precise, guideline-referenced clinical language.
- Frame responses around clinical decision support — first-line vs \
  alternative options, dosing adjustments for special populations, \
  contraindications, and monitoring parameters.
- Reference Nigerian or African clinical guidelines where available \
  (e.g., FMOH, WHO Afro, NHIA); fall back to international guidelines \
  (WHO, NICE, AHA) where local guidelines are absent.
- Responses should support but not replace clinical judgement.
- For prescribing decisions involving complex comorbidities, recommend \
  specialist review where appropriate."""

ROLE_NURSE = """\
The user is a licensed NURSE.

Response rules:
- Use clinical language appropriate for nursing practice.
- Focus on medication administration, monitoring parameters, patient \
  education, and recognising adverse effects or toxicity.
- Include practical nursing considerations — route of administration, \
  rate of infusion, compatibility, and observation intervals.
- Highlight when a query requires physician escalation or prescriber \
  authorisation before action is taken.
- Acknowledge Nigeria's primary healthcare context where nurses may \
  work semi-autonomously in some settings."""

ROLE_OTHER = """\
The user is a HEALTH PROFESSIONAL (not a physician, pharmacist, or nurse) \
— this may include a medical laboratory scientist, physiotherapist, \
dietitian, radiographer, or community health worker.

Response rules:
- Use professional clinical language but do not assume deep \
  pharmacological training.
- Tailor the response to the most likely relevance of the query to \
  their scope of practice — e.g., for an MLS, focus on \
  drug-laboratory interference; for a dietitian, focus on \
  drug-nutrient interactions.
- If the query falls outside their typical scope of practice, \
  acknowledge this respectfully and direct them to the appropriate \
  professional (pharmacist or physician).
- Keep responses practical and role-relevant."""

# Lookup for selecting role prompt by key
ROLE_PROMPTS = {
    "patient": ROLE_PATIENT,
    "pharmacist": ROLE_PHARMACIST,
    "physician": ROLE_PHYSICIAN,
    "nurse": ROLE_NURSE,
    "other": ROLE_OTHER,
    "other_health_professional": ROLE_OTHER,
}


# ──────────────────────────────────────────────────────────────────────
# 4. RAG CONTEXT TEMPLATE  (dynamic — NOT cached, changes every request)
# ──────────────────────────────────────────────────────────────────────

RAG_CONTEXT_TEMPLATE = """\
RETRIEVED CONTEXT:
-----------------
{context_chunks}
-----------------

USER ROLE: {role}
USER QUESTION: {query}

Answer based strictly on the retrieved context above. \
If the context does not contain sufficient information to answer \
safely and accurately, state this clearly rather than inferring \
beyond what is provided."""

# Injected in the user turn when the vector DB returns no results.
# Prevents the model from hallucinating as if RAG context exists.
NO_CONTEXT_NOTE = """\
NOTE: No relevant information was found in the knowledge base for this query.
Answer from your general training knowledge and apply extra caution — \
especially for dosing, interactions, and high-risk populations. Do not \
announce the missing retrieval context to the user unless it materially \
limits the answer. When in doubt, ask one clarifying question or advise \
checking with the appropriate clinician rather than speculating."""

IMAGE_ANALYSIS_PROMPT = """\
The user has attached one or more images. Examine each image carefully.
If an image appears to be a PRESCRIPTION, transcribe visible text, identify
medications, dosages, instructions, and flag illegible parts. If it appears
to be a PILL or PACKAGING, identify the drug name, strength, and manufacturer
where visible. If it appears to show a BODY PART, describe observations, do
not diagnose, and suggest consulting a clinician if needed. If it appears to
be a LAB RESULT, summarize findings, flag abnormal values, and suggest
possible diagnoses cautiously without being assertive. For unclear
prescriptions, recommend confirming with a pharmacist."""

DOCUMENT_ANALYSIS_PROMPT = """\
The user has attached one or more documents. Review the extracted or parsed
content. If a document appears to be a PRESCRIPTION or ORDER, list all
medications, dosages, routes, and flag interactions or unusual dosing. If it
appears to be a LAB REPORT, flag abnormal values and explain clinical
significance. If it is a DRUG MONOGRAPH, extract the specific information the
user asks about. If it is a SPREADSHEET, interpret the data and summarize key
findings. Relate the analysis to the user's specific question. If content is
truncated or unclear, say so."""


# ──────────────────────────────────────────────────────────────────────
# 5. HELPERS
# ──────────────────────────────────────────────────────────────────────

def format_retrieved_chunks(chunks: list) -> str:
    """Format a list of Qdrant result dicts into the RAG context block.

    Each chunk dict is expected to have:
        - ``text``   (str) — the retrieved passage
        - ``source`` (str) — document name / guideline title (optional)

    Returns a single formatted string ready for RAG_CONTEXT_TEMPLATE.
    """
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "Unknown source")
        text = chunk.get("text", "").strip()
        lines.append(f"[Chunk {i} — Source: {source}]\n{text}")
    return "\n\n".join(lines)


def build_system_message(role: str = "patient") -> str:
    """Assemble the full system message from static prompt blocks."""
    role_prompt = ROLE_PROMPTS.get(role, ROLE_PATIENT)
    return "\n\n".join([
        SYSTEM_PROMPT,
        CLARIFYING_QUESTIONS,
        HALLUCINATION_CONTROL,
        SAFETY_ESCALATION,
        CONVERSATION_STYLE,
        role_prompt,
    ])


def build_user_message(
    query: str,
    chunks: list | None = None,
    role: str = "patient",
) -> str:
    """Build the user-turn message, injecting RAG context when available.

    Args:
        query:   The user's question.
        chunks:  List of dicts returned by the RAG retrieval step
                 (each with ``text`` and ``source`` keys).
                 Pass ``None`` or ``[]`` when Qdrant returns nothing.
        role:    The user's professional role (used as a reminder in the
                 context block alongside the system message role).

    Returns:
        A formatted string to send as the user turn to the LLM.
    """
    if chunks:
        context_str = format_retrieved_chunks(chunks)
        return RAG_CONTEXT_TEMPLATE.format(
            context_chunks=context_str,
            role=role,
            query=query,
        )
    # No RAG context: prepend the no-context note so the model is aware.
    return f"{NO_CONTEXT_NOTE}\n\nUSER ROLE: {role}\nUSER QUESTION: {query}"


def _format_document_sections(document_sections: list | None) -> str:
    """Format extracted Office document text for the dynamic user turn."""
    if not document_sections:
        return ""

    sections = []
    for section in document_sections:
        name = section.get("name", "document")
        text = (section.get("text") or "").strip()
        if not text:
            text = "[No readable text was extracted.]"
        sections.append(
            f"DOCUMENT CONTENT (from: {name}):\n---\n{text}\n---"
        )
    return "\n\n".join(sections)


def _build_attachment_user_text(
    query: str,
    chunks: list | None,
    role: str,
    attachments: list | None,
    document_sections: list | None,
) -> str:
    """Build the text part that accompanies optional multimodal attachments."""
    attachments = attachments or []
    has_image = any(item.get("kind") == "image" for item in attachments)
    has_document = any(item.get("kind") == "file" for item in attachments) or bool(document_sections)

    prompt_blocks = []
    if has_image:
        prompt_blocks.append(IMAGE_ANALYSIS_PROMPT)
    if has_document:
        prompt_blocks.append(DOCUMENT_ANALYSIS_PROMPT)

    document_block = _format_document_sections(document_sections)
    if document_block:
        prompt_blocks.append(document_block)

    prompt_blocks.append(build_user_message(query, chunks=chunks, role=role))
    return "\n\n".join(prompt_blocks)


def _build_user_content(text_part: str, attachments: list | None):
    """Return OpenRouter-compatible user content, string or multimodal parts."""
    attachments = attachments or []
    if not attachments:
        return text_part

    content = [{"type": "text", "text": text_part}]
    for attachment in attachments:
        if attachment.get("kind") == "image":
            content.append({
                "type": "image_url",
                "image_url": {"url": attachment["data_url"]},
            })
        elif attachment.get("kind") == "file":
            content.append({
                "type": "file",
                "file": {
                    "filename": attachment["name"],
                    "file_data": attachment["data_url"],
                },
            })
    return content


def _select_models(attachments: list | None) -> list[str]:
    """Return an ordered list of models to try (primary, then fallback)."""
    if any(item.get("kind") == "image" for item in attachments or []):
        models = [settings.OPENROUTER_VISION_MODEL]
        fallback = settings.OPENROUTER_VISION_MODEL_FALLBACK
        if fallback and fallback != models[0]:
            models.append(fallback)
        return models
    return [settings.OPENROUTER_TEXT_MODEL]


def _select_model(attachments: list | None) -> str:
    """Backward-compatible single-model selector used by older tests."""
    return _select_models(attachments)[0]


def _response_token_budget(is_complex: bool) -> int:
    if is_complex:
        return settings.OPENROUTER_REASONING_MAX_TOKENS
    return settings.OPENROUTER_TEXT_MAX_TOKENS


def _length_limit_message() -> str:
    return (
        "\n\nI am stopping here so the answer stays within RxChat's response limit. "
        "Follow-up question: Which part would you like me to expand next?"
    )


def _build_pdf_plugin(attachments: list | None):
    if any(item.get("type") == "application/pdf" for item in attachments or []):
        return [{
            "id": "file-parser",
            "pdf": {"engine": "cloudflare-ai"},
        }]
    return None


# ──────────────────────────────────────────────────────────────────────
# 6. LLM CLIENT  (OpenRouter only)
# ──────────────────────────────────────────────────────────────────────

def _get_client(api_key=None):
    """Return an OpenAI-compatible client configured for OpenRouter.

    Returns:
        OpenAI client instance, or None if the API key is missing.
    """
    api_key = api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set — cannot create LLM client")
        return None

    return OpenAI(
        api_key=api_key,
        base_url=settings.OPENROUTER_BASE_URL,
        default_headers={
            'HTTP-Referer': 'https://rxchat.dev',
            'X-Title': 'RxChat',
        },
    )


# ──────────────────────────────────────────────────────────────────────
# 7. COMPLEXITY CLASSIFICATION
# ──────────────────────────────────────────────────────────────────────

# Keywords / patterns that suggest the query needs deeper reasoning.
_COMPLEX_INDICATORS = [
    # Drug interactions & polypharmacy
    "interaction", "interactions", "combine", "combining", "together with",
    "concomitant", "polypharmacy", "contraindicated",
    # Dosing adjustments
    "dose adjustment", "renal impairment", "hepatic impairment",
    "creatinine clearance", "gfr", "weight-based", "paediatric dosing",
    "neonatal", "elderly dosing", "pregnancy", "breastfeeding",
    # High-risk scenarios
    "overdose", "toxicity", "narrow therapeutic index", "therapeutic drug monitoring",
    "warfarin", "lithium", "digoxin", "phenytoin", "aminoglycoside",
    # Multi-step clinical reasoning
    "differential", "first-line", "second-line", "step-up", "step-down",
    "algorithm", "guideline", "protocol", "compare", "versus", " vs ",
    # Professional-depth queries
    "pharmacokinetic", "pharmacodynamic", "mechanism of action",
    "bioavailability", "half-life", "cyp450", "cyp3a4", "cyp2d6",
]


def _is_complex_query(query: str, role: str) -> bool:
    """Determine if a query warrants deeper reasoning.

    Returns True when the question involves drug interactions, dosing
    adjustments, or multi-step clinical reasoning — regardless of role.
    """
    query_lower = query.lower()

    # Check for complexity indicators
    for indicator in _COMPLEX_INDICATORS:
        if indicator in query_lower:
            return True

    # Multiple drug names (crude heuristic: query has 2+ capitalised
    # words that could be drug names after removing common words)
    words = query.split()
    if len(words) >= 15:  # Longer queries tend to be more complex
        return True

    return False


# ──────────────────────────────────────────────────────────────────────
# 8. STREAMING ENTRYPOINT
# ──────────────────────────────────────────────────────────────────────

def stream_ai_response(
    user_message,
    conversation_history=None,
    role="patient",
    attachments=None,
    document_sections=None,
):
    """Stream an AI response for a pharmacy-related query.

    Uses OpenRouter as the LLM provider.

    Yields text chunks as they arrive from the LLM.

    Args:
        user_message:  The user's question.
        conversation_history:  List of prior messages
            [{'role': 'user'|'assistant', 'content': '...'}]
        role:  One of 'patient', 'pharmacist', 'physician', 'nurse', 'other'.
        attachments:  List of image/PDF attachment dicts to send to OpenRouter.
        document_sections:  Extracted Office document text blocks.

    Yields:
        str: Text chunks as they are generated.
    """
    attachments = attachments or []
    document_sections = document_sections or []

    primary_key = settings.OPENROUTER_API_KEY
    backup_key = settings.OPENROUTER_BACKUP_API_KEY
    key_attempts = [("primary", primary_key)]
    if backup_key:
        key_attempts.append(("backup", backup_key))

    if not primary_key and not backup_key:
        logger.error("No OpenRouter API key is configured")
        yield _get_fallback_response()
        return

    models_to_try = _select_models(attachments)

    use_reasoner = _is_complex_query(user_message, role)

    logger.info(
        f"Provider: OpenRouter | Models: {models_to_try} "
        f"(role={role}, complex={use_reasoner}, attachments={len(attachments)}, "
        f"documents={len(document_sections)})"
    )

    system_message = build_system_message(role)

    messages = [{"role": "system", "content": system_message}]

    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    # Retrieve relevant drug-knowledge chunks from Qdrant
    # Qdrant Cloud Inference handles embedding server-side — no external API call
    chunks = retrieve_context(user_message, top_k=10)
    if chunks:
        logger.info(f"RAG: {len(chunks)} chunks retrieved from Qdrant")
    else:
        logger.info("RAG: No chunks retrieved — LLM will answer from training data")

    user_text_part = _build_attachment_user_text(
        user_message,
        chunks=chunks,
        role=role,
        attachments=attachments,
        document_sections=document_sections,
    )

    messages.append({
        "role": "user",
        "content": _build_user_content(user_text_part, attachments),
    })

    pdf_plugin = _build_pdf_plugin(attachments)

    last_error = None
    for model_index, model in enumerate(models_to_try):
        # Build request kwargs for this model
        create_kwargs = dict(
            model=model,
            messages=messages,
            stream=True,
        )
        create_kwargs["max_tokens"] = _response_token_budget(use_reasoner)
        if not use_reasoner:
            create_kwargs["temperature"] = 0.7

        if pdf_plugin:
            create_kwargs["extra_body"] = {"plugins": pdf_plugin}

        for attempt_index, (key_label, api_key) in enumerate(key_attempts):
            if not api_key:
                continue

            client = _get_client(api_key)
            if not client:
                continue

            emitted_any = False
            try:
                stream = client.chat.completions.create(**create_kwargs)
                finish_reason = None
                for chunk in stream:
                    choice = chunk.choices[0]
                    finish_reason = getattr(choice, "finish_reason", None) or finish_reason
                    delta = choice.delta
                    if delta.content:
                        emitted_any = True
                        yield delta.content
                if finish_reason == "length":
                    yield _length_limit_message()
                return
            except Exception as e:
                last_error = e
                logger.error(
                    f"LLM API error (model={model}, {key_label} key): {e}"
                )

                has_next_key = attempt_index < len(key_attempts) - 1
                if not emitted_any and has_next_key:
                    logger.info("Retrying with backup API key")
                    continue

                if emitted_any:
                    yield (
                        "\n\nThe response was interrupted before RxChat could finish. "
                        "Please send the message again if you need a complete answer. "
                        "Follow-up question: Which section should I continue with first?"
                    )
                    return
                break  # break key loop, try next model

        # If we reach here, all keys failed for this model — try next model
        has_next_model = model_index < len(models_to_try) - 1
        if has_next_model:
            next_model = models_to_try[model_index + 1]
            logger.info(f"Model {model} failed, falling back to {next_model}")
            continue

    logger.error(f"All model/key attempts failed: {last_error}")
    yield _get_fallback_response()


def get_ai_response(user_message, conversation_history=None, role="patient", attachments=None, document_sections=None):
    """Non-streaming wrapper — collects the full response.

    Kept for backward compatibility and non-streaming endpoints.
    """
    parts = []
    for chunk in stream_ai_response(
        user_message,
        conversation_history,
        role,
        attachments=attachments,
        document_sections=document_sections,
    ):
        parts.append(chunk)
    return "".join(parts)


def _get_fallback_response():
    """Generic fallback when no LLM API is available."""
    return (
        "I'm currently unable to process your request. "
        "Please try again shortly or consult a licensed healthcare professional.\n\n"
        "⚠️ For emergencies, please call emergency services or visit "
        "the nearest hospital immediately.\n\n"
        "Follow-up question: What medication or symptom would you like help with next?"
    )
