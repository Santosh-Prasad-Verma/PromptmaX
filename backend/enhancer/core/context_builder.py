"""Context building module for PromptX."""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..utils.constants import DOMAIN_ROLES, ENHANCEMENT_STRUCTURES
from ..utils.helpers import timer

logger = logging.getLogger('enhancer')


@dataclass
class PromptSection:
    name: str
    header: str
    content: str
    priority: int
    is_essential: bool


class ContextBuilder:
    """
    Builds rich context sections for enhanced prompts.
    Generates each section (role, task, context, constraints, etc.)
    based on the analysis results.
    """

    def __init__(self):
        self.domain_roles = DOMAIN_ROLES
        self.structures = ENHANCEMENT_STRUCTURES

    @timer
    def build_sections(self, analysis, complexity_level: str,
                       user_preferences: Optional[Dict] = None) -> List[PromptSection]:
        """Build all sections for the enhanced prompt."""
        intent = analysis.intent.primary_intent
        domain = analysis.intent.domain
        task_type = analysis.intent.task_type
        missing = analysis.quality.missing_elements

        structure = self.structures.get(intent, self.structures.get('generate'))
        sections = []

        for section_name in structure:
            builder_method = getattr(self, f'_build_{section_name}', None)
            if builder_method:
                import inspect
                sig = inspect.signature(builder_method)
                params = sig.parameters

                kwargs = {
                    'intent': intent,
                    'domain': domain,
                    'task_type': task_type,
                    'missing': missing,
                    'complexity': complexity_level,
                    'preferences': user_preferences,
                }

                filtered = {}
                for key, value in kwargs.items():
                    if key in params:
                        filtered[key] = value
                section = builder_method(analysis=analysis, **filtered)
                if section and section.content.strip():
                    sections.append(section)

        # Add chain-of-thought for complex tasks
        if complexity_level in ('high', 'expert'):
            sections.append(self._build_chain_of_thought(analysis, complexity_level))

        # Add negative instructions (what to avoid)
        sections.append(self._build_negative_instructions(analysis, intent))

        # Add quality criteria
        sections.append(self._build_quality_criteria(analysis, intent, domain))

        return [s for s in sections if s and s.content.strip()]

    def _build_role(self, analysis, intent, domain, **kwargs) -> PromptSection:
        """Build role/persona section."""
        if analysis.quality.element_presence.get('role', False):
            # Extract existing role from text
            import re
            role_match = re.search(
                r'(?:act as|you are|as a)\s+(.+?)(?:\.|$)',
                analysis.original_text, re.IGNORECASE
            )
            content = role_match.group(0) if role_match else self.domain_roles.get(domain, self.domain_roles['general'])
        else:
            content = self.domain_roles.get(domain, self.domain_roles['general'])

        return PromptSection(
            name='role',
            header='Role & Expertise',
            content=content,
            priority=100,
            is_essential=True,
        )

    def _build_task(self, analysis, intent, domain, task_type, **kwargs) -> PromptSection:
        """Build main task description."""
        original = analysis.original_text.strip()

        # Enhance the task description based on analysis
        task_parts = [original]

        # Add keyword emphasis for clarity
        if analysis.keywords and analysis.quality.clarity < 0.6:
            task_parts.append(
                f"\nKey focus areas: {', '.join(analysis.keywords[:7])}"
            )

        # Add sub-tasks for complex requests
        if analysis.complexity.requires_decomposition and analysis.complexity.sub_tasks:
            task_parts.append("\nBreak this into the following sub-tasks:")
            for i, sub in enumerate(analysis.complexity.sub_tasks, 1):
                task_parts.append(f"  {i}. {sub}")

        return PromptSection(
            name='task',
            header='Task',
            content='\n'.join(task_parts),
            priority=95,
            is_essential=True,
        )

    def _build_context(self, analysis, domain, missing, **kwargs) -> PromptSection:
        """Build context section."""
        if 'context' not in missing:
            return PromptSection(
                name='context', header='Context',
                content='Context is provided within the task description above.',
                priority=85, is_essential=False,
            )

        context_parts = []

        if domain != 'general':
            context_parts.append(f"Domain: {domain.replace('_', ' ').title()}")

        if analysis.entities:
            entities_str = ', '.join(set(e['text'] for e in analysis.entities[:10]))
            context_parts.append(f"Key entities referenced: {entities_str}")

        if analysis.programming_language:
            context_parts.append(f"Programming language: {analysis.programming_language.title()}")

        if analysis.requires_external_knowledge:
            context_parts.append(
                "Note: This request may involve current/recent information. "
                "Use the most up-to-date knowledge available."
            )

        if not context_parts:
            context_parts.append(
                "Apply your expertise to the fullest extent. "
                "Consider industry best practices and common use cases."
            )

        return PromptSection(
            name='context',
            header='Context',
            content='\n'.join(context_parts),
            priority=85,
            is_essential=True,
        )

    def _build_requirements(self, analysis, intent, complexity, **kwargs) -> PromptSection:
        """Build requirements section."""
        reqs = self._get_intent_requirements(intent, complexity)

        # Add requirements inferred from the prompt
        if analysis.has_negation:
            reqs.append("Pay careful attention to any stated exclusions or limitations")

        if analysis.is_multi_part:
            reqs.append("Address each part of the request comprehensively")

        return PromptSection(
            name='requirements',
            header='Requirements',
            content='\n'.join(f"- {r}" for r in reqs),
            priority=80,
            is_essential=True,
        )

    def _build_specifications(self, analysis, intent, **kwargs) -> PromptSection:
        """Build technical specifications for code tasks."""
        if intent != 'code':
            return None

        specs = [
            "Write clean, well-documented, production-ready code",
            "Include comprehensive error handling and edge cases",
            "Add type hints/annotations where applicable",
            "Follow the language's official style guide",
            "Include docstrings/JSDoc for all public functions and classes",
        ]

        if analysis.programming_language:
            lang_specs = {
                'python': [
                    "Follow PEP 8 style guidelines",
                    "Use f-strings for string formatting",
                    "Include __init__.py and proper module structure if multiple files",
                ],
                'javascript': [
                    "Use ES6+ syntax (const, let, arrow functions, destructuring)",
                    "Handle promises with async/await",
                    "Include JSDoc comments",
                ],
                'typescript': [
                    "Use proper TypeScript types (avoid 'any')",
                    "Define interfaces for complex data structures",
                    "Use strict mode",
                ],
            }
            extra = lang_specs.get(analysis.programming_language, [])
            specs.extend(extra)

        return PromptSection(
            name='specifications',
            header='Technical Specifications',
            content='\n'.join(f"- {s}" for s in specs),
            priority=78,
            is_essential=True,
        )

    def _build_code_requirements(self, analysis, **kwargs) -> PromptSection:
        """Alias for specifications in code context."""
        return self._build_specifications(analysis, intent='code', **kwargs)

    def _build_technical_context(self, analysis, **kwargs) -> PromptSection:
        """Build technical context for code tasks."""
        parts = []
        if analysis.programming_language:
            parts.append(f"Primary language: {analysis.programming_language.title()}")
        if analysis.code_blocks:
            parts.append(f"Code samples provided: {len(analysis.code_blocks)}")

        tech_keywords = [kw for kw in analysis.keywords if kw in [
            'api', 'database', 'server', 'client', 'frontend', 'backend',
            'rest', 'graphql', 'docker', 'cloud', 'testing', 'deployment'
        ]]
        if tech_keywords:
            parts.append(f"Technologies involved: {', '.join(tech_keywords)}")

        if not parts:
            parts.append("Apply modern development best practices and design patterns.")

        return PromptSection(
            name='technical_context',
            header='Technical Context',
            content='\n'.join(parts),
            priority=83,
            is_essential=False,
        )

    def _build_output_format(self, analysis, intent, missing, **kwargs) -> PromptSection:
        """Build output format specification."""
        if 'output_format' not in missing:
            return PromptSection(
                name='output_format', header='Output Format',
                content='Follow the format specified in the task.',
                priority=70, is_essential=False,
            )

        format_specs = self._get_format_for_intent(intent, analysis.intent.task_type)

        return PromptSection(
            name='output_format',
            header='Output Format',
            content=format_specs,
            priority=70,
            is_essential=True,
        )

    def _build_constraints(self, analysis, intent, missing, complexity, **kwargs) -> PromptSection:
        """Build constraints section."""
        constraints = []

        if 'constraints' not in missing:
            constraints.append("Follow the constraints specified in the task.")
        else:
            constraints.extend([
                "Stay focused on the specific request—avoid tangential content",
                "Be thorough but concise—no unnecessary filler",
                "Clearly state any assumptions you make",
            ])

        if intent == 'code':
            constraints.extend([
                "Ensure code is runnable without modifications (unless clearly noted)",
                "Use modern language features and idioms",
                "Handle edge cases and invalid inputs gracefully",
            ])

        if complexity in ('high', 'expert'):
            constraints.extend([
                "If the task is ambiguous, state the interpretation you're using",
                "Provide reasoning for significant design/architectural decisions",
            ])

        return PromptSection(
            name='constraints',
            header='Constraints & Guidelines',
            content='\n'.join(f"- {c}" for c in constraints),
            priority=65,
            is_essential=True,
        )

    def _build_audience(self, analysis, missing, **kwargs) -> PromptSection:
        """Build audience specification."""
        if 'audience' not in missing:
            return None

        return PromptSection(
            name='audience',
            header='Target Audience',
            content=(
                "Assume the reader has working knowledge of the domain "
                "but appreciates clear explanations and well-organized content."
            ),
            priority=60,
            is_essential=False,
        )

    def _build_depth(self, analysis, complexity, **kwargs) -> PromptSection:
        """Build depth specification."""
        depth_map = {
            'low': "Provide a concise, focused response covering the essentials.",
            'medium': "Provide a thorough response with explanations and examples where helpful.",
            'high': "Provide an in-depth, comprehensive response with detailed explanations, examples, and edge cases.",
            'expert': "Provide an expert-level, exhaustive response covering all aspects, edge cases, trade-offs, and advanced considerations.",
        }

        return PromptSection(
            name='depth',
            header='Expected Depth',
            content=depth_map.get(complexity, depth_map['medium']),
            priority=55,
            is_essential=False,
        )

    def _build_examples_request(self, analysis, missing, **kwargs) -> PromptSection:
        """Request examples in the output."""
        if 'examples' not in missing:
            return None

        return PromptSection(
            name='examples_request',
            header='Examples',
            content="Include practical, relevant examples to illustrate key concepts and demonstrate usage.",
            priority=50,
            is_essential=False,
        )

    def _build_testing(self, analysis, **kwargs) -> PromptSection:
        """Build testing requirements for code tasks."""
        return PromptSection(
            name='testing',
            header='Testing',
            content=(
                "- Include unit tests or test cases demonstrating the solution works\n"
                "- Cover normal cases, edge cases, and error cases\n"
                "- Use the language's standard testing framework"
            ),
            priority=45,
            is_essential=False,
        )

    def _build_documentation(self, analysis, **kwargs) -> PromptSection:
        """Build documentation requirements."""
        return PromptSection(
            name='documentation',
            header='Documentation',
            content=(
                "- Include clear comments explaining non-obvious logic\n"
                "- Add a brief usage section showing how to use the solution\n"
                "- Document any prerequisites or dependencies"
            ),
            priority=40,
            is_essential=False,
        )

    def _build_analysis_task(self, analysis, **kwargs) -> PromptSection:
        return self._build_task(analysis, 'analyze', analysis.intent.domain, analysis.intent.task_type)

    def _build_framework(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='framework',
            header='Analysis Framework',
            content=(
                "Use a structured analytical approach:\n"
                "1. Define the scope and criteria\n"
                "2. Gather and organize relevant information\n"
                "3. Analyze systematically\n"
                "4. Draw evidence-based conclusions\n"
                "5. Provide actionable recommendations"
            ),
            priority=75, is_essential=False,
        )

    def _build_data_sources(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='data_sources', header='Data Sources',
            content="Use the information provided in the task. Clearly state when making assumptions.",
            priority=72, is_essential=False,
        )

    def _build_source_description(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='source_description', header='Source',
            content="See the content/data provided in the task above.",
            priority=85, is_essential=False,
        )

    def _build_target_description(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='target_description', header='Target Output',
            content="Transform according to the specifications in the task.",
            priority=83, is_essential=False,
        )

    def _build_transformation_rules(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='transformation_rules', header='Transformation Rules',
            content=(
                "- Preserve the core meaning and intent\n"
                "- Apply the requested changes consistently\n"
                "- Maintain quality and correctness throughout"
            ),
            priority=80, is_essential=False,
        )

    def _build_content_to_summarize(self, analysis, **kwargs) -> PromptSection:
        return self._build_task(analysis, 'summarize', analysis.intent.domain, analysis.intent.task_type)

    def _build_summary_type(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='summary_type', header='Summary Approach',
            content="Provide a balanced summary capturing key points, main arguments, and essential details.",
            priority=78, is_essential=False,
        )

    def _build_key_focus(self, analysis, **kwargs) -> PromptSection:
        if analysis.keywords:
            content = f"Focus on: {', '.join(analysis.keywords[:7])}"
        else:
            content = "Focus on the most important and actionable information."
        return PromptSection(
            name='key_focus', header='Key Focus Areas',
            content=content, priority=75, is_essential=False,
        )

    def _build_length(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='length', header='Length',
            content="Provide a comprehensive but concise summary. Aim for clarity over brevity.",
            priority=65, is_essential=False,
        )

    def _build_problem_description(self, analysis, **kwargs) -> PromptSection:
        return self._build_task(analysis, 'fix', analysis.intent.domain, analysis.intent.task_type)

    def _build_error_details(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='error_details', header='Error Details',
            content="Include any error messages, stack traces, or unexpected behavior described above.",
            priority=82, is_essential=False,
        )

    def _build_expected_behavior(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='expected_behavior', header='Expected Behavior',
            content="Clearly state what the correct/expected behavior should be.",
            priority=80, is_essential=False,
        )

    def _build_topic(self, analysis, **kwargs) -> PromptSection:
        return self._build_task(analysis, 'brainstorm', analysis.intent.domain, analysis.intent.task_type)

    def _build_quantity(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='quantity', header='Quantity',
            content="Provide at least 5-10 diverse, well-thought-out ideas.",
            priority=70, is_essential=False,
        )

    def _build_evaluation_criteria(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='evaluation_criteria', header='Evaluation Criteria',
            content=(
                "For each idea, briefly note:\n"
                "- Feasibility\n"
                "- Potential impact\n"
                "- Key considerations"
            ),
            priority=65, is_essential=False,
        )

    def _build_task_to_teach(self, analysis, **kwargs) -> PromptSection:
        return self._build_task(analysis, 'instruct', analysis.intent.domain, analysis.intent.task_type)

    def _build_prerequisites(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='prerequisites', header='Prerequisites',
            content="State any prerequisites or prior knowledge needed before following the instructions.",
            priority=73, is_essential=False,
        )

    def _build_tips(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='tips', header='Tips & Warnings',
            content="Include helpful tips, common pitfalls to avoid, and important warnings.",
            priority=45, is_essential=False,
        )

    def _build_research_topic(self, analysis, **kwargs) -> PromptSection:
        return self._build_task(analysis, 'research', analysis.intent.domain, analysis.intent.task_type)

    def _build_scope(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='scope', header='Scope',
            content="Define clear boundaries for the research. Focus on the most relevant and impactful aspects.",
            priority=78, is_essential=False,
        )

    def _build_sources(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='sources', header='Sources',
            content="Reference established, authoritative sources. Indicate confidence levels.",
            priority=70, is_essential=False,
        )

    def _build_citations(self, analysis, **kwargs) -> PromptSection:
        return PromptSection(
            name='citations', header='Citations',
            content="Cite sources where possible. Use a consistent citation format.",
            priority=50, is_essential=False,
        )

    def _build_chain_of_thought(self, analysis, complexity) -> PromptSection:
        """Add chain-of-thought instruction for complex tasks."""
        return PromptSection(
            name='chain_of_thought',
            header='Reasoning Approach',
            content=(
                "Before providing your final answer:\n"
                "1. Identify the core problem or question\n"
                "2. Break it down into manageable components\n"
                "3. Consider multiple approaches and their trade-offs\n"
                "4. Select the best approach with clear reasoning\n"
                "5. Implement/execute step by step\n"
                "6. Review your response for completeness and accuracy"
            ),
            priority=30,
            is_essential=False,
        )

    def _build_negative_instructions(self, analysis, intent) -> PromptSection:
        """What to avoid."""
        avoids = [
            "Do NOT include generic filler or fluff content",
            "Do NOT make assumptions without stating them",
            "Do NOT provide outdated or deprecated solutions",
        ]

        if intent == 'code':
            avoids.extend([
                "Do NOT use deprecated APIs or libraries",
                "Do NOT ignore error handling",
                "Do NOT write untested code without noting limitations",
            ])

        return PromptSection(
            name='negative_instructions',
            header='Important: Avoid',
            content='\n'.join(f"- {a}" for a in avoids),
            priority=25,
            is_essential=False,
        )

    def _build_quality_criteria(self, analysis, intent, domain) -> PromptSection:
        """Quality checklist for the response."""
        criteria = [
            "Directly and completely addresses the stated request",
            "Is factually accurate and technically correct",
            "Is well-organized with clear structure",
            "Provides actionable, practical information",
            "Uses appropriate level of detail for the audience",
        ]

        return PromptSection(
            name='quality_criteria',
            header='Quality Checklist',
            content='\n'.join(f"- [ ] {c}" for c in criteria),
            priority=20,
            is_essential=False,
        )

    def _get_intent_requirements(self, intent: str, complexity: str) -> List[str]:
        """Get requirements specific to an intent."""
        base_reqs = {
            'generate': [
                "Produce original, high-quality content",
                "Maintain consistent tone and style throughout",
                "Ensure logical flow and coherence",
            ],
            'explain': [
                "Start with a clear, concise overview",
                "Use analogies and examples to illustrate complex points",
                "Progress logically from foundational to advanced concepts",
            ],
            'code': [
                "Write clean, maintainable, production-quality code",
                "Include comprehensive error handling",
                "Follow established design patterns where appropriate",
                "Optimize for readability first, then performance",
            ],
            'analyze': [
                "Provide objective, evidence-based analysis",
                "Consider multiple perspectives",
                "Support conclusions with clear reasoning",
                "Identify limitations and uncertainties",
            ],
            'fix': [
                "Identify the root cause of the problem",
                "Explain why the issue occurs",
                "Provide a clear, tested solution",
                "Suggest preventive measures",
            ],
            'transform': [
                "Maintain data integrity during transformation",
                "Validate input before processing",
                "Clearly document any data loss or changes",
            ],
            'summarize': [
                "Capture all key points and main arguments",
                "Maintain the original meaning and nuance",
                "Organize by importance or theme",
            ],
            'brainstorm': [
                "Provide diverse, creative ideas",
                "Include both conventional and unconventional approaches",
                "Briefly evaluate feasibility for each idea",
            ],
            'instruct': [
                "Use clear, numbered steps",
                "Include prerequisites and warnings",
                "Verify each step is actionable and testable",
            ],
            'research': [
                "Use authoritative sources",
                "Present balanced perspectives",
                "Distinguish facts from opinions/theories",
            ],
        }

        reqs = base_reqs.get(intent, [
            "Provide accurate, relevant, well-structured information",
            "Be thorough yet concise",
        ])

        if complexity in ('high', 'expert'):
            reqs.append("Provide in-depth analysis with advanced considerations")
            reqs.append("Address edge cases and potential pitfalls")

        return reqs

    def _get_format_for_intent(self, intent: str, task_type: str) -> str:
        """Get format specification for intent and task type."""
        formats = {
            'code_web_frontend': (
                "Provide:\n"
                "1. Complete, runnable code files\n"
                "2. Clear file structure if multiple files\n"
                "3. Inline comments for complex logic\n"
                "4. Brief setup/installation instructions\n"
                "5. Browser compatibility notes if relevant"
            ),
            'code_web_backend': (
                "Provide:\n"
                "1. Complete API/endpoint implementation\n"
                "2. Request/response format documentation\n"
                "3. Error handling and status codes\n"
                "4. Database schema if applicable\n"
                "5. Example requests/responses"
            ),
            'code_general': (
                "Provide:\n"
                "1. Well-commented, complete source code\n"
                "2. Usage examples\n"
                "3. Input/output documentation\n"
                "4. Dependencies and setup notes"
            ),
            'generate_article': (
                "Structure as:\n"
                "1. Compelling headline\n"
                "2. Engaging introduction with hook\n"
                "3. Well-organized body with subheadings\n"
                "4. Conclusion with key takeaways\n"
                "5. Clear, readable paragraphs"
            ),
            'generate_email': (
                "Format as:\n"
                "1. Subject line\n"
                "2. Appropriate greeting\n"
                "3. Concise, purposeful body\n"
                "4. Clear call-to-action\n"
                "5. Professional closing"
            ),
            'explain_concept': (
                "Structure as:\n"
                "1. One-line definition\n"
                "2. Accessible analogy\n"
                "3. Detailed explanation\n"
                "4. Practical examples\n"
                "5. Common misconceptions (if any)\n"
                "6. Further learning resources"
            ),
            'analyze_general': (
                "Organize analysis as:\n"
                "1. Executive summary\n"
                "2. Methodology/framework used\n"
                "3. Detailed findings\n"
                "4. Conclusions\n"
                "5. Recommendations"
            ),
        }

        # Try specific, then intent-level, then default
        format_text = formats.get(task_type)
        if not format_text:
            format_text = formats.get(f"{intent}_general")
        if not format_text:
            format_text = (
                "Provide a clear, well-structured response with:\n"
                "- Organized sections with headers\n"
                "- Key points highlighted\n"
                "- Examples where helpful\n"
                "- Actionable takeaways"
            )

        return format_text
