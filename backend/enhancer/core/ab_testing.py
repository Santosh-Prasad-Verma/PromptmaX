import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from .ai_client import generate_with_fallback
from .quality_scorer import QualityScorer

logger = logging.getLogger('enhancer')


def generate_ab_variations(prompt, preferred_model=None, api_key=None):
    scorer = QualityScorer()

    def fetch_variation(style_prompt, max_tokens):
        result = generate_with_fallback(style_prompt, max_tokens, preferred_model=preferred_model, api_key=api_key)
        quality = scorer.score(result['text'])
        return {
            'text': result['text'],
            'length': len(result['text']),
            'model': result['model'],
            'quality': quality.overall,
        }

    concise_prompt = f"Make this prompt concise and direct (max 150 words) focusing only on core deliverables:\n{prompt}"
    detailed_prompt = (
        f"Expand this prompt into a comprehensive, highly-detailed technical specification.\n"
        f"Include deep technical requirements, system architecture, edge cases, and performance considerations:\n{prompt}"
    )
    structured_prompt = (
        f"Rewrite this prompt using an advanced prompt engineering framework.\n"
        f"Structure it with: Context & Role, Request, Architecture Diagram (as D2 in ```d2``` block),\n"
        f"Action Steps, Tone & Constraints, and Extras/Examples.\n"
        f"Here is the original prompt:\n{prompt}"
    )

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_c = executor.submit(fetch_variation, concise_prompt, 800)
            future_d = executor.submit(fetch_variation, detailed_prompt, 2048)
            future_s = executor.submit(fetch_variation, structured_prompt, 2048)
            concise = future_c.result(timeout=45)
            detailed = future_d.result(timeout=45)
            structured = future_s.result(timeout=45)
        return {'concise': concise, 'detailed': detailed, 'structured': structured}
    except TimeoutError:
        logger.warning("A/B test generation timed out for one or more variations")
        return {
            'concise': {'text': prompt, 'length': len(prompt), 'model': 'timeout', 'quality': 0.0},
            'detailed': {'text': prompt, 'length': len(prompt), 'model': 'timeout', 'quality': 0.0},
            'structured': {'text': prompt, 'length': len(prompt), 'model': 'timeout', 'quality': 0.0},
        }
    except Exception as e:
        logger.error(f"A/B test generation failed: {e}")
        return {
            'concise': {'text': prompt, 'length': len(prompt), 'model': 'fallback', 'quality': 0.0},
            'detailed': {'text': prompt, 'length': len(prompt), 'model': 'fallback', 'quality': 0.0},
            'structured': {'text': prompt, 'length': len(prompt), 'model': 'fallback', 'quality': 0.0},
        }


def compare_variations(original, variations):
    scorer = QualityScorer()
    for key in variations:
        quality = scorer.score(variations[key]['text'])
        variations[key]['quality'] = quality.overall
    best_key = max(variations.keys(), key=lambda k: variations[k].get('quality', 0))
    return {
        'variations': variations,
        'recommendation': {
            'best_variation': best_key,
            'reason': f'{best_key.capitalize()} version has the highest quality score',
        },
    }
