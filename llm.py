import asyncio
import logging
import random
from google import genai
from google.genai import errors , types

from app.config import settings


log = logging.getLogger("gateway.llm")
client = genai.Client(api_key=settings.gemini_api_key)

def	to_contents(messages):
    return[
         types.Content(
            role="model" if	m.role	==	"assistant"	else "user",
            parts=[types.Part(text=m.text)],
            )
            for	m in messages
    ]

def is_temporary(e):
    if isinstance(e, errors.APIError):
        return e.code in (429, 500, 503)
    name = type(e).__name__
    return "Connect" in name or "Timeout" in name    #nework problem 

async def generate(messages , system , temperature):
    config = types.GenerateContentConfig(system_instruction=system , temperature=temperature)
    for attempt in range(settings.max_retries):
        try:
            response = await client.aio.models.generate_content(
                model = settings.default_model,
                contents= to_contents(messages),
                config = config
            )
            u = response.usage_metadata
            return response.text or "",(u.prompt_token_count or 0) , (u.candidates_token_count or 0)
        except Exception as e:
            if attempt == settings.max_retries - 1 or not is_temporary(e):
                raise
            wait = 2 ** attempt + random.random()
            log.warning(f",temporary error ({type(e).__name__})retrying in {wait:.1f}s")
            await asyncio.sleep(wait)