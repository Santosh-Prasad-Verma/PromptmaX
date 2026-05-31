"""Refinement engine module for PromptX."""

import logging
from typing import List
from dataclasses import dataclass

from .quality_scorer import QualityScorer, QualityScore
from .ai_client import generate_with_fallback
from ..utils.helpers import timer

logger = logging.getLogger('enhancer')

@dataclass
class RefinementIteration:
    iteration: int
    action: str
    score_before: float
    score_after: float
    changes_made: List[str]

@dataclass
class RefinementResult:
    original_text: str
    refined_text: str
    iterations: List[RefinementIteration]
    total_iterations: int
    score_improvement: float
    final_score: float

class RefinementEngine:
    def __init__(self):
        self.scorer = QualityScorer()

    @timer
    def refine(self, text: str, target_score: float = 0.85, max_iterations: int = 3) -> RefinementResult:
        """Iteratively refine text using an LLM critique loop until quality threshold is met."""
        current_text = text
        iterations = []
        original_score = self.scorer.score(current_text)
        current_score = original_score

        for i in range(max_iterations):
            if current_score.overall >= target_score:
                logger.info(f"Refinement target reached at iteration {i}")
                break

            logger.info(f"Initiating auto-heal loop iteration {i+1}. Current score: {current_score.overall}")
            
            # The Auto-Heal Feedback Prompt
            auto_heal_prompt = f"""You are a master prompt auto-healer. The following prompt scored a {int(current_score.overall * 100)}/100.
We need it to be at least {int(target_score * 100)}/100.

CURRENT PROMPT:
{current_text}

WEAKNESSES:
- Clarity Score: {current_score.detail_scores.get('clarity', 0)}
- Detail Score: {current_score.detail_scores.get('specificity', 0)}
- Completeness Score: {current_score.detail_scores.get('completeness', 0)}

Rewrite this prompt to fix the weaknesses. Output ONLY the new, perfect prompt. Do not output conversational filler.
"""
            
            # Make the LLM call
            result = generate_with_fallback(auto_heal_prompt, max_tokens=1500)
            refined_text = result.get('text', '').strip()
            
            # Score the new version
            new_score = self.scorer.score(refined_text)

            if new_score.overall > current_score.overall:
                iterations.append(RefinementIteration(
                    iteration=i + 1,
                    action="LLM Auto-Heal",
                    score_before=current_score.overall,
                    score_after=new_score.overall,
                    changes_made=["Auto-healed via LLM structural critique"]
                ))
                current_text = refined_text
                current_score = new_score
            else:
                logger.info("Auto-heal did not improve the score. Stopping refinement early.")
                break

        return RefinementResult(
            original_text=text,
            refined_text=current_text,
            iterations=iterations,
            total_iterations=len(iterations),
            score_improvement=current_score.overall - original_score.overall,
            final_score=current_score.overall
        )
