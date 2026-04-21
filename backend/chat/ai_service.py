"""
RxChat AI Service — Prompt definitions and AI response pipeline.

Supports multiple LLM providers via PROVIDER_REGISTRY in settings:
  - NVIDIA NIM  (build.nvidia.com → DeepSeek v3.2)
  - DeepSeek    (platform.deepseek.com)
  - OpenRouter  (openrouter.ai — aggregated access)

The active provider is selected per-request (user preference stored
client-side and sent with each API call).  If the chosen provider
fails, the service falls back through the remaining available
providers automatically.

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
# 1. SYSTEM PROMPT  (always sent — cached by DeepSeek)
# ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are RxChat, an AI-powered healthcare assistant designed for use \
in Nigeria. You assist patients, pharmacists, physicians, nurses, and \
other health professionals with drug information, medication counselling, \
and clinical decision support.

Core rules you must always follow:
- Base your answers ONLY on the retrieved context provided to you.
- If the retrieved context does not contain enough information to answer \
  confidently, say so clearly. Do not guess or fabricate.
- Adjust your language, tone, and depth based on the user's role.
- Always recommend consulting a licensed healthcare professional for \
  prescribing decisions, emergencies, or anything beyond your scope.
- Keep Nigeria's disease burden, NAFDAC-approved medicines, NHIA \
  guidelines, and locally available drugs in mind at all times.
- Do not reference sources in your response to users."""


# ──────────────────────────────────────────────────────────────────────
# 2. BEHAVIOUR RULES  (static — cached by DeepSeek)
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
If the retrieved context does not contain a clear and sufficient answer, \
respond with:

"I don't have enough information in my current knowledge base to answer \
this accurately. Please consult a licensed healthcare professional or \
refer to an authoritative clinical guideline."

Do not attempt to fill knowledge gaps using information not present in \
the retrieved context. It is safer to acknowledge uncertainty than to \
provide an inaccurate clinical answer."""

SAFETY_ESCALATION = """\
Automatically add a safety disclaimer and recommend immediate professional \
consultation when the query involves any of the following:

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
Answer from your general training knowledge, but be explicit about this \
limitation and apply extra caution — especially for dosing, interactions, \
and high-risk populations. When in doubt, recommend consulting a licensed \
healthcare professional rather than speculating."""


# ──────────────────────────────────────────────────────────────────────
# 5. HELPERS
# ──────────────────────────────────────────────────────────────────────

def format_retrieved_chunks(chunks: list) -> str:
    """Format a list of ChromaDB result dicts into the RAG context block.

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
    """Assemble the full system message from static prompt blocks.

    Static content is ordered first so DeepSeek's prefix cache reuses it
    across requests. Only the role section varies (5 possible variants,
    each cached independently).
    """
    role_prompt = ROLE_PROMPTS.get(role, ROLE_PATIENT)
    return "\n\n".join([
        SYSTEM_PROMPT,
        CLARIFYING_QUESTIONS,
        HALLUCINATION_CONTROL,
        SAFETY_ESCALATION,
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


# ──────────────────────────────────────────────────────────────────────
# 6. LLM CLIENT  (multi-provider — NVIDIA / DeepSeek / OpenRouter)
# ──────────────────────────────────────────────────────────────────────

def _get_provider_config(provider: str | None = None) -> dict | None:
    """Resolve a provider slug to its registry config.

    Falls back through available providers if the requested one is
    unavailable or not specified.
    """
    registry = settings.PROVIDER_REGISTRY

    # Try the explicitly requested provider first
    if provider and provider in registry:
        cfg = registry[provider]
        if cfg['available']:
            return cfg
        logger.warning(
            f"Requested provider '{provider}' has no API key — trying fallbacks"
        )

    # Fallback: try the default, then all others
    fallback_order = [settings.DEFAULT_LLM_PROVIDER] + [
        k for k in registry if k != settings.DEFAULT_LLM_PROVIDER
    ]
    for slug in fallback_order:
        cfg = registry.get(slug)
        if cfg and cfg['available']:
            logger.info(f"Using fallback provider: {slug}")
            return cfg

    return None


def _get_client(provider: str | None = None):
    """Return an OpenAI-compatible client for the given provider.

    Args:
        provider: One of 'nvidia', 'deepseek', 'openrouter', or None
                  (uses default + fallback chain).

    Returns:
        Tuple of (OpenAI client, provider_config dict) or (None, None).
    """
    cfg = _get_provider_config(provider)
    if not cfg:
        logger.error("No LLM provider available — all API keys missing")
        return None, None

    extra_headers = {}
    # OpenRouter requires HTTP-Referer and X-Title headers
    if cfg.get('base_url', '').startswith('https://openrouter.ai'):
        extra_headers = {
            'HTTP-Referer': 'https://rxchat.dev',
            'X-Title': 'RxChat',
        }

    client = OpenAI(
        api_key=cfg['api_key'],
        base_url=cfg['base_url'],
        default_headers=extra_headers or None,
    )
    return client, cfg


def get_available_providers() -> list[dict]:
    """Return a list of available providers for the frontend.

    Each item has: slug, name, model_display, is_default.
    """
    registry = settings.PROVIDER_REGISTRY
    default = settings.DEFAULT_LLM_PROVIDER
    providers = []
    for slug, cfg in registry.items():
        if cfg['available']:
            providers.append({
                'slug': slug,
                'name': cfg['name'],
                'model_display': cfg['model_display'],
                'is_default': slug == default,
            })
    return providers


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
    """Determine if a query warrants the reasoning model.

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

def _get_model_name(cfg: dict, use_reasoner: bool) -> str:
    """Return the correct model identifier for the given provider config.

    DeepSeek direct has separate reasoner/chat models; NVIDIA NIM and
    OpenRouter use a single model identifier.
    """
    if use_reasoner and 'model_reasoner' in cfg:
        return cfg['model_reasoner']
    return cfg['model']


def stream_ai_response(
    user_message,
    conversation_history=None,
    role="patient",
    provider=None,
):
    """Stream an AI response for a pharmacy-related query.

    Supports NVIDIA NIM, DeepSeek, and OpenRouter.  Provider is selected
    by the ``provider`` argument (sent from frontend); falls back through
    available providers if the selected one fails.

    Yields text chunks as they arrive from the LLM.

    Args:
        user_message:  The user's question.
        conversation_history:  List of prior messages
            [{'role': 'user'|'assistant', 'content': '...'}]
        role:  One of 'patient', 'pharmacist', 'physician', 'nurse', 'other'.
        provider:  One of 'nvidia', 'deepseek', 'openrouter', or None.

    Yields:
        str: Text chunks as they are generated.
    """
    client, cfg = _get_client(provider)
    if not client:
        yield _get_fallback_response()
        return

    try:
        use_reasoner = _is_complex_query(user_message, role)
        model = _get_model_name(cfg, use_reasoner)

        logger.info(
            f"Provider: {cfg['name']} | Model: {model} "
            f"(role={role}, reasoner={use_reasoner})"
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
        chunks = retrieve_context(user_message, top_k=5)
        if chunks:
            logger.info(f"RAG: {len(chunks)} chunks retrieved from Qdrant")
        else:
            logger.info("RAG: No chunks retrieved — LLM will answer from training data")

        messages.append({
            "role": "user",
            "content": build_user_message(user_message, chunks=chunks, role=role),
        })

        # Reasoner model parameters differ slightly
        create_kwargs = dict(
            model=model,
            messages=messages,
            stream=True,
        )
        if use_reasoner:
            create_kwargs["max_tokens"] = 4096
        else:
            create_kwargs["temperature"] = 0.7
            create_kwargs["max_tokens"] = 2048

        stream = client.chat.completions.create(**create_kwargs)

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    except Exception as e:
        logger.error(f"LLM API error ({cfg['name']}): {e}")
        yield _get_fallback_response()


def get_ai_response(user_message, conversation_history=None, role="patient", provider=None):
    """Non-streaming wrapper — collects the full response.

    Kept for backward compatibility and non-streaming endpoints.
    """
    parts = []
    for chunk in stream_ai_response(user_message, conversation_history, role, provider):
        parts.append(chunk)
    return "".join(parts)


def _get_fallback_response():
    """Generic fallback when no LLM API is available."""
    return (
        "I'm currently unable to process your request. "
        "Please try again shortly or consult a licensed healthcare professional.\n\n"
        "⚠️ For emergencies, please call emergency services or visit "
        "the nearest hospital immediately."
    )
