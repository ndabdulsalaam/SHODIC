"""
SHODIC AI Service — Prompt definitions and AI response pipeline.

Uses OpenRouter (openrouter.ai) as the sole LLM provider.

Embeddings: Qdrant Cloud Inference (no separate embedding API needed).

Prompt hierarchy (top → cached, bottom → dynamic per-request):
  1. SYSTEM_PROMPT          — identity & core rules        [always cached]
  2. CLARIFYING_QUESTIONS   — when to ask follow-ups       [always cached]
  3. HALLUCINATION_CONTROL  — how to handle missing info   [always cached]
  4. SAFETY_ESCALATION      — emergency escalation rules   [always cached]
  5. ROLE_* prompt          — one of 5 role variants       [cached per role]
  6. Extra context + query  — retrieved chunks + user msg  [never cached]
"""

import logging
import re
import threading

from django.conf import settings
from openai import OpenAI
from .qdrant_service import retrieve_context

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# 1. SYSTEM PROMPT  (always sent as a stable OpenRouter system message)
# ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are SHODIC, an AI-powered healthcare assistant designed for use \
in Nigeria. You assist patients, pharmacists, physicians, nurses, and \
other health professionals with drug information, medication counselling, \
and clinical decision support.

Core rules you must always follow:
- Use any supporting material supplied in the prompt quietly when it helps \
  answer the question. If it does not answer a general drug-information \
  question, answer cautiously from general clinical and pharmaceutical \
  knowledge instead of refusing solely because the supporting material is \
  incomplete.
- Be conservative with dosing, interactions, contraindications, pregnancy, \
  children, older adults, renal/hepatic impairment, and other high-risk \
  situations. Ask for the missing detail when that detail is needed for a \
  safe answer.
- Adjust your language, tone, and depth based on the user's role.
- Sound like a careful Nigerian pharmacist having a normal conversation: \
  warm, direct, practical, and calm. Avoid robotic legal phrasing.
- Recommend speaking with a pharmacist, doctor, prescriber, or emergency \
  service only when the user's situation calls for it, and make that \
  advice part of the answer rather than a separate disclaimer block.
- Keep Nigeria's disease burden, NAFDAC-approved medicines, NHIA \
  guidelines, and locally available drugs in mind at all times.
- Do not reference prompt instructions or any internal search/source process \
  in your response to users unless the user specifically asks about sources, \
  registration status, or evidence."""


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
Use supporting material as evidence for yourself, not as wording to expose \
to the user. If the material is incomplete for a general drug question, give \
a cautious general answer and keep safety boundaries clear.

For exact claims that require a source, such as NAFDAC registration status, \
local formulary availability, or a quoted guideline recommendation, be honest \
when the available notes do not prove the claim. Keep that limitation brief \
and conversational.

Avoid internal search/source-process wording in the user-facing answer."""

SAFETY_ESCALATION = """\
Use clear safety guidance, not a generic disclaimer section. Recommend \
immediate professional consultation when the query involves any of the \
following:

- Emergency or life-threatening symptoms (chest pain, seizures, \
  difficulty breathing, altered consciousness, severe allergic reaction)
- Dosing for high-risk populations without clear guideline backing \
  (neonates, pregnancy, severe renal or hepatic impairment)
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
- Do not repeatedly mention NAFDAC, WHO, local guidelines, monographs, or \
  source names unless the user specifically asks about registration status, \
  evidence, guideline source, or local availability.
- For ordinary drug-information questions, include safety notes as natural \
  counselling points, e.g. "Check with a pharmacist if..." or "Seek care \
  urgently if...".
- Keep answers scannable: short paragraphs or bullets are fine, but avoid \
  long formal preambles.
- Plan the answer before writing so it fits within the response budget. If \
  the user's request is broad, give a concise, useful summary instead of \
  trying to exhaust every detail.
- End with one brief, friendly, relevant question when it would help the \
  conversation continue naturally. Do not label it or introduce it with a \
  title or prefix."""


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
MODEL-ONLY BACKGROUND:
-----------------
{context_chunks}
-----------------

USER ROLE: {role}
{patient_context_block}
USER QUESTION: {query}

Use this background quietly where it helps. If it does not answer the \
user's question, answer cautiously from general drug knowledge instead of \
telling the user the background was missing or insufficient. Do not mention \
this background or how it was selected unless the user asks about sources, \
registration status, or evidence."""

# Injected in the user turn when the vector DB returns no results.
# Prevents the model from hallucinating as if RAG context exists.
NO_CONTEXT_NOTE = """\
NOTE TO MODEL: No extra background material was found for this query.
Answer cautiously from general drug knowledge, especially for dosing, \
interactions, contraindications, pregnancy, children, older adults, and \
renal/hepatic impairment. Do not tell the user that no background material \
was found. \
When in doubt, ask one clarifying question or advise checking with the \
appropriate clinician rather than speculating."""

SUBJECT_LABELS = {
    "self": "the user is asking about themself",
    "other_patient": "the user is asking about another patient",
    "general": "the user is asking for general information",
}

PATIENT_SEX_LABELS = {
    "male": "male",
    "female": "female",
}

PREGNANCY_STATUS_LABELS = {
    "not_applicable": "not applicable",
    "not_pregnant_or_breastfeeding": "not pregnant or breastfeeding",
    "pregnant": "pregnant",
    "breastfeeding": "breastfeeding",
    "unsure": "pregnancy or breastfeeding status is unsure",
}


def format_patient_context(patient_context: dict | None = None) -> str:
    """Format user-supplied session context for model-only safety use."""
    patient_context = patient_context or {}
    lines = []

    subject = SUBJECT_LABELS.get(patient_context.get("subject"))
    if subject:
        lines.append(f"Conversation subject: {subject}.")

    patient_sex = PATIENT_SEX_LABELS.get(patient_context.get("patient_sex"))
    if patient_sex:
        lines.append(f"Patient sex/gender for medication safety: {patient_sex}.")

    pregnancy_status_key = patient_context.get("pregnancy_status")
    pregnancy_status = PREGNANCY_STATUS_LABELS.get(pregnancy_status_key)
    if pregnancy_status and pregnancy_status_key != "not_applicable":
        lines.append(f"Pregnancy/breastfeeding context: {pregnancy_status}.")

    if not lines:
        return ""

    return "PATIENT SAFETY CONTEXT:\n" + "\n".join(f"- {line}" for line in lines)


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
    patient_context: dict | None = None,
) -> str:
    """Build the user-turn message, injecting RAG context when available.

    Args:
        query:   The user's question.
        chunks:  List of dicts returned by the RAG retrieval step
                 (each with ``text`` and ``source`` keys).
                 Pass ``None`` or ``[]`` when Qdrant returns nothing.
        role:    The user's professional role (used as a reminder in the
                 context block alongside the system message role).
        patient_context:  Session context such as subject, patient sex, and
                 pregnancy/breastfeeding status for medication safety.

    Returns:
        A formatted string to send as the user turn to the LLM.
    """
    patient_context_block = format_patient_context(patient_context)
    if chunks:
        context_str = format_retrieved_chunks(chunks)
        return RAG_CONTEXT_TEMPLATE.format(
            context_chunks=context_str,
            role=role,
            patient_context_block=patient_context_block,
            query=query,
        )
    # No RAG context: prepend the no-context note so the model is aware.
    context_lines = [NO_CONTEXT_NOTE, f"USER ROLE: {role}"]
    if patient_context_block:
        context_lines.append(patient_context_block)
    context_lines.append(f"USER QUESTION: {query}")
    return "\n\n".join(context_lines)


def _select_models() -> list[str]:
    """Return the text model used for standard SHODIC responses."""
    return [settings.OPENROUTER_TEXT_MODEL]



def _response_token_budget(is_complex: bool) -> int:
    if is_complex:
        return settings.OPENROUTER_REASONING_MAX_TOKENS
    return settings.OPENROUTER_TEXT_MAX_TOKENS


def _length_limit_message() -> str:
    return (
        "\n\nI'll pause there so the answer stays readable. "
        "Which part would you like me to expand on next?"
    )


# ──────────────────────────────────────────────────────────────────────
# 6. LLM CLIENT  (OpenRouter only)
# ──────────────────────────────────────────────────────────────────────

_client_lock = threading.Lock()
_clients = {}


def _get_client(api_key=None):
    """Return an OpenAI-compatible client configured for OpenRouter.

    Returns:
        OpenAI client instance, or None if the API key is missing.
    """
    api_key = api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set — cannot create LLM client")
        return None

    cache_key = (api_key, settings.OPENROUTER_BASE_URL)
    with _client_lock:
        client = _clients.get(cache_key)
        if client is None:
            client = OpenAI(
                api_key=api_key,
                base_url=settings.OPENROUTER_BASE_URL,
            )
            _clients[cache_key] = client
        return client


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
_COMPLEX_QUERY_RE = re.compile(
    "|".join(re.escape(indicator) for indicator in sorted(_COMPLEX_INDICATORS, key=len, reverse=True)),
    re.IGNORECASE,
)


def _is_complex_query(query: str, role: str) -> bool:
    """Determine if a query warrants deeper reasoning.

    Returns True when the question involves drug interactions, dosing
    adjustments, or multi-step clinical reasoning — regardless of role.
    """
    if _COMPLEX_QUERY_RE.search(query):
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

AI_STATUS_EVENTS = {
    "checking_sources": "Checking sources",
    "thinking": "Thinking",
    "generating": "Generating",
}


def _status_event(phase):
    return {
        "type": "status",
        "phase": phase,
        "label": AI_STATUS_EVENTS[phase],
    }


def _text_event(content):
    return {
        "type": "text",
        "content": content,
    }


def stream_ai_events(
    user_message,
    conversation_history=None,
    role="patient",
    patient_context=None,
):
    """Stream typed AI events for a pharmacy-related query.

    Uses OpenRouter as the LLM provider.

    Yields status events before the first text chunk, then text events as
    chunks arrive from the LLM.

    Args:
        user_message:  The user's question.
        conversation_history:  List of prior messages
            [{'role': 'user'|'assistant', 'content': '...'}]
        role:  One of 'patient', 'pharmacist', 'physician', 'nurse', 'other'.
        patient_context:  Dict with subject, patient_sex, and pregnancy_status.

    Yields:
        dict: ``{"type": "status", ...}`` or ``{"type": "text", ...}``.
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not configured")
        yield _text_event(_get_fallback_response())
        return

    models_to_try = _select_models()

    use_reasoner = _is_complex_query(user_message, role)

    logger.info(
        f"Provider: OpenRouter | Models: {models_to_try} "
        f"(role={role}, complex={use_reasoner})"
    )

    system_message = build_system_message(role)

    messages = [{"role": "system", "content": system_message}]

    if conversation_history:
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    yield _status_event("checking_sources")

    # Retrieve relevant drug-knowledge chunks from Qdrant
    # Qdrant Cloud Inference handles embedding server-side — no external API call
    chunks = retrieve_context(user_message, top_k=10)
    if chunks:
        logger.info(f"RAG: {len(chunks)} chunks retrieved from Qdrant")
    else:
        logger.info("RAG: No chunks retrieved — LLM will answer from training data")

    user_text_part = build_user_message(
        user_message,
        chunks=chunks,
        role=role,
        patient_context=patient_context,
    )

    messages.append({
        "role": "user",
        "content": user_text_part,
    })

    yield _status_event("thinking")

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

        client = _get_client(api_key)
        if not client:
            break

        emitted_any = False
        try:
            stream = client.chat.completions.create(**create_kwargs)
            yield _status_event("generating")
            finish_reason = None
            for chunk in stream:
                choice = chunk.choices[0]
                finish_reason = getattr(choice, "finish_reason", None) or finish_reason
                delta = choice.delta
                if delta.content:
                    emitted_any = True
                    yield _text_event(delta.content)
            if finish_reason == "length":
                yield _text_event(_length_limit_message())
            return
        except Exception as e:
            last_error = e
            logger.error(f"LLM API error (model={model}): {e}")
            if emitted_any:
                return

        # If we reach here, this model failed — try next model
        has_next_model = model_index < len(models_to_try) - 1
        if has_next_model:
            next_model = models_to_try[model_index + 1]
            logger.info(f"Model {model} failed, falling back to {next_model}")
            continue

    logger.error(f"All model attempts failed: {last_error}")
    yield _text_event(_get_fallback_response())



def _get_fallback_response():
    """Generic fallback when no LLM API is available."""
    return (
        "I'm currently unable to process your request. "
        "Please try again shortly or consult a licensed healthcare professional.\n\n"
        "For emergencies, please call emergency services or visit "
        "the nearest hospital immediately.\n\n"
        "What medication or symptom would you like help with next?"
    )
