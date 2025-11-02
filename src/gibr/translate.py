"""Translation utilities for issue titles."""

import logging
import re

from deep_translator import GoogleTranslator


def detect_cyrillic(text: str) -> bool:
    """Check if text contains Cyrillic characters.
    
    Args:
        text: The text to check
        
    Returns:
        True if text contains Cyrillic characters, False otherwise
    """
    cyrillic_pattern = re.compile(r'[а-яА-ЯёЁ]')
    return bool(cyrillic_pattern.search(text))


def translate_to_english(text: str, source_lang: str = "ru") -> str:
    """Translate text to English.
    
    Args:
        text: The text to translate
        source_lang: The source language code (default: "ru" for Russian)
        
    Returns:
        Translated text, or original text if translation fails
    """
    if not text or not text.strip():
        return text
    
    try:
        translator = GoogleTranslator(source=source_lang, target="en")
        translated = translator.translate(text)
        logging.debug(f"Translated '{text}' to '{translated}'")
        return translated
    except Exception as e:
        logging.warning(f"Translation failed: {e}. Using original text.")
        return text


def auto_translate_if_needed(text: str) -> str:
    """Automatically translate text to English if it contains Cyrillic characters.
    
    Args:
        text: The text to potentially translate
        
    Returns:
        Translated text if Cyrillic was detected, otherwise original text
    """
    if not text:
        return text
    
    if detect_cyrillic(text):
        logging.info(f"Detected Cyrillic text: '{text}', translating to English...")
        return translate_to_english(text)
    
    return text

