import os
import re
import asyncio
import logging

log = logging.getLogger(__name__)

def generate_voiceover(script, output_path="output/voice.mp3"):
    """Generate Malayalam voiceover using edge-tts."""
    os.makedirs("output", exist_ok=True)
    text = clean_text(script)
    log.info(f"Generating Malayalam voiceover ({len(text)} chars)...")

    if not text.strip():
        raise RuntimeError("No text to speak.")

    # Try Malayalam voice
    for attempt in range(3):
        try:
            asyncio.run(_tts_malayalam(text, output_path))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                log.info(f"Malayalam voiceover saved: {output_path}")
                return output_path
        except Exception as e:
            log.warning(f"Malayalam TTS attempt {attempt+1}: {e}")

    # Fallback to gTTS with Malayalam
    try:
        from gtts import gTTS
        gTTS(text=text, lang="ml", slow=False).save(output_path)
        log.info(f"gTTS Malayalam fallback saved: {output_path}")
        return output_path
    except Exception as e:
        log.warning(f"gTTS Malayalam failed: {e}")
        # Final fallback — English voice
        from gtts import gTTS
        gTTS(text=text, lang="en", slow=False).save(output_path)
        return output_path

async def _tts_malayalam(text, path):
    import edge_tts
    # Malayalam voice — cheerful and kid-friendly
    communicate = edge_tts.Communicate(
        text,
        voice="ml-IN-MidhunNeural",  # Malayalam male voice
        rate="+10%",
        pitch="+5Hz"
    )
    await asyncio.wait_for(communicate.save(path), timeout=60)

def clean_text(script):
    text = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', script, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\*+', '', text)
    return re.sub(r'\s+', ' ', text).strip()
