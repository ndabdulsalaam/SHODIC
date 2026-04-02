"""
RxChat AI Service — Google Gemini integration with LangChain.
Uses RAG when ChromaDB has data, falls back to direct Gemini otherwise.
"""

import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# System prompt for the pharmacy assistant
SYSTEM_PROMPT = """You are RxChat, a knowledgeable and friendly AI pharmacy assistant. Your role is to provide
helpful, accurate information about medications, drug interactions, side effects, dosage guidelines,
and over-the-counter recommendations.

IMPORTANT GUIDELINES:
1. Always provide evidence-based pharmaceutical information
2. Include relevant warnings and contraindications
3. Format responses with clear headings, bullet points, and bold text for key terms
4. Use ⚠️ Warning markers for serious safety concerns
5. Always remind users to consult their healthcare provider for personalized advice
6. If unsure about something, clearly state your uncertainty
7. Never diagnose conditions or prescribe specific treatments
8. Be helpful for a global audience — mention generic drug names alongside brand names
9. Keep responses thorough but concise

If provided with context from drug databases, use that information to ground your responses.
If no context is available, use your general pharmaceutical knowledge but note the limitation."""


def get_gemini_response(user_message, conversation_history=None):
    """
    Get a response from Google Gemini for a pharmacy-related query.
    
    Args:
        user_message: The user's question
        conversation_history: List of previous messages [{'role': 'user'|'assistant', 'content': '...'}]
    
    Returns:
        str: The AI response text
    """
    api_key = settings.GEMINI_API_KEY
    
    if not api_key:
        return _get_fallback_response(user_message)
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        # Build conversation contents
        contents = []
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                role = 'user' if msg['role'] == 'user' else 'model'
                contents.append(genai.types.Content(
                    role=role,
                    parts=[genai.types.Part(text=msg['content'])]
                ))
        
        # Add current message
        contents.append(genai.types.Content(
            role='user',
            parts=[genai.types.Part(text=user_message)]
        ))
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=2048,
            ),
        )
        
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _get_fallback_response(user_message)


def _get_fallback_response(user_message):
    """Fallback responses when Gemini API is unavailable."""
    msg = user_message.lower()
    
    if any(word in msg for word in ['metformin', 'diabetes']):
        return """**Metformin** is one of the most commonly prescribed medications for **Type 2 Diabetes**.

**Common Side Effects:**
- Nausea and stomach upset (usually temporary)
- Diarrhea
- Metallic taste in mouth
- Reduced appetite

**Key Information:**
- Take with food to minimize stomach upset
- Avoid excessive alcohol consumption
- Regular kidney function monitoring recommended

⚠️ Warning: Always consult your doctor before starting or changing diabetes medication.

*Note: This is a pre-loaded response. Connect your Gemini API key for personalized, AI-powered responses.*"""
    
    if any(word in msg for word in ['ibuprofen', 'nsaid', 'pain']):
        return """**Ibuprofen** is a nonsteroidal anti-inflammatory drug (NSAID) used for pain, inflammation, and fever.

**Common Side Effects:**
- Stomach upset or pain
- Nausea, dizziness

**Drug Interactions to watch:**
- **Blood thinners** (warfarin) — increased bleeding risk
- **ACE inhibitors** — reduced blood pressure effect

**Recommended Dosage (Adults):**
- 200–400mg every 4–6 hours as needed
- Maximum: 1200mg/day (OTC)

⚠️ Warning: Long-term use may increase risk of heart attack, stroke, and GI bleeding. Consult your pharmacist.

*Note: This is a pre-loaded response. Connect your Gemini API key for personalized, AI-powered responses.*"""
    
    if any(word in msg for word in ['allerg', 'antihistamine']):
        return """For **seasonal allergies**, effective OTC options include:

**Non-drowsy Antihistamines:**
- **Cetirizine** (Zyrtec) — once daily
- **Loratadine** (Claritin) — minimal drowsiness
- **Fexofenadine** (Allegra) — least sedating

**Nasal Sprays:**
- **Fluticasone** (Flonase) — steroid spray, very effective

Start medications before allergy season begins for best results.

⚠️ Always consult a pharmacist if you're taking other medications.

*Note: This is a pre-loaded response. Connect your Gemini API key for personalized, AI-powered responses.*"""
    
    return f"""Thank you for your question about "{user_message[:60]}".

I'd be happy to help with medication-related questions. Here are some things I can assist with:

- **Medication information** — Side effects, dosage, how they work
- **Drug interactions** — Safety of combining medications
- **OTC recommendations** — Suggestions for common symptoms
- **Dosage guidelines** — Proper usage information

⚠️ Always consult a qualified healthcare professional for personalized medical advice.

*Note: Connect your Gemini API key in `backend/.env` for full AI-powered responses.*"""
