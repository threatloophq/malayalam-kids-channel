import os
import logging
from groq import Groq

log = logging.getLogger(__name__)

def get_video_transcript(video_id):
    """Get English transcript from YouTube video."""
    if not video_id:
        return None
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB"])
        full_text = " ".join([t["text"] for t in transcript])
        log.info(f"Transcript: {len(full_text)} chars")
        return full_text
    except Exception as e:
        log.warning(f"Transcript failed for {video_id}: {e}")
        return None

def translate_to_malayalam(text, topic=""):
    """Translate English kids content to Malayalam."""
    api_key = os.getenv("GROQ_API_KEY", "")
    client = Groq(api_key=api_key)

    # Chunk if too long
    if len(text) > 3000:
        text = text[:3000]

    prompt = f"""You are an expert Malayalam translator specializing in kids content for Kerala children.

Translate this English kids content to Malayalam (മലയാളം).

RULES:
- Use simple, fun Malayalam that young children (3-10 years) will understand
- Keep character names in original language
- Make it playful and engaging — use expressions kids love
- Sound phrases should stay similar (songs, rhymes keep their rhythm)
- Animal sounds stay universal (moo, woof, meow)
- Keep numbers in both Malayalam and English
- Make it sound natural when read aloud

English content:
{text}

Write ONLY the Malayalam translation:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.3,
    )
    translated = response.choices[0].message.content.strip()
    log.info(f"Malayalam translation: {len(translated)} chars")
    return translated

def generate_malayalam_kids_script(topic, video_id=""):
    """Get transcript and translate, or generate fresh Malayalam kids content."""
    # Try transcript first
    if video_id:
        transcript = get_video_transcript(video_id)
        if transcript:
            log.info(f"Translating transcript for: {topic}")
            return translate_to_malayalam(transcript, topic)

    # Generate fresh Malayalam kids content
    log.info(f"Generating fresh Malayalam kids content for: {topic}")
    api_key = os.getenv("GROQ_API_KEY", "")
    client = Groq(api_key=api_key)

    prompt = f"""You are a Malayalam kids YouTube content creator in Kerala.

Write a fun, engaging 3-5 minute kids video script in Malayalam about:
{topic}

RULES:
- Target age: 3-10 years
- Use simple Malayalam words children understand
- Make it fun, exciting and educational
- Include sound effects cues like [കൊട്ടിക്കലി!] [ഹഹ!]
- Add moral lesson at the end
- Include visual cues [VISUAL CUE: scene description]
- Keep sentences short and clear

Write the complete Malayalam script:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
