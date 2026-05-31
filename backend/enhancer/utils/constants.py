"""
Central configuration constants for the entire PromptX engine.
Every pattern, template, weight, and mapping lives here.
"""


# ═══════════════════════════════════════════════════════════
# INTENT CLASSIFICATION
# ═══════════════════════════════════════════════════════════

INTENT_PATTERNS = {
    'generate': {
        'keywords': [
            'write', 'create', 'generate', 'make', 'build', 'compose',
            'draft', 'produce', 'develop', 'design', 'construct',
            'formulate', 'prepare', 'craft', 'author',
        ],
        'weight': 1.0,
    },
    'explain': {
        'keywords': [
            'explain', 'describe', 'tell me', 'what is', 'how does',
            'why', 'elaborate', 'clarify', 'define', 'illustrate',
            'break down', 'walk me through', 'help me understand',
        ],
        'weight': 1.0,
    },
    'analyze': {
        'keywords': [
            'analyze', 'evaluate', 'assess', 'review', 'examine',
            'compare', 'contrast', 'investigate', 'diagnose', 'audit',
            'inspect', 'critique', 'benchmark', 'measure',
        ],
        'weight': 1.0,
    },
    'transform': {
        'keywords': [
            'convert', 'transform', 'translate', 'change', 'modify',
            'rewrite', 'refactor', 'restructure', 'adapt', 'migrate',
            'port', 'optimize', 'improve', 'upgrade',
        ],
        'weight': 1.0,
    },
    'summarize': {
        'keywords': [
            'summarize', 'sum up', 'brief', 'shorten', 'condense',
            'tldr', 'digest', 'overview', 'recap', 'abstract',
            'outline', 'key points', 'highlights',
        ],
        'weight': 1.0,
    },
    'code': {
        'keywords': [
            'code', 'program', 'function', 'script', 'algorithm',
            'debug', 'implement', 'api', 'endpoint', 'class',
            'module', 'library', 'framework', 'deploy', 'test',
            'unit test', 'integration', 'python', 'javascript',
            'typescript', 'java', 'c++', 'rust', 'golang',
        ],
        'weight': 1.2,  # Higher weight because code tasks are very specific
    },
    'brainstorm': {
        'keywords': [
            'brainstorm', 'ideas', 'suggest', 'recommend', 'list',
            'options', 'alternatives', 'possibilities', 'propose',
            'come up with', 'think of',
        ],
        'weight': 0.9,
    },
    'instruct': {
        'keywords': [
            'how to', 'steps', 'guide', 'tutorial', 'instructions',
            'walkthrough', 'procedure', 'recipe', 'playbook',
            'checklist', 'workflow',
        ],
        'weight': 1.0,
    },
    'fix': {
        'keywords': [
            'fix', 'solve', 'resolve', 'troubleshoot', 'repair',
            'correct', 'patch', 'debug', 'error', 'issue', 'bug',
            'problem', 'broken', 'not working', 'failing',
        ],
        'weight': 1.1,
    },
    'research': {
        'keywords': [
            'research', 'find', 'search', 'look up', 'investigate',
            'explore', 'discover', 'survey', 'study', 'review literature',
        ],
        'weight': 0.9,
    },
    'idea': {
        'keywords': [
            'idea', 'ideas', 'suggest', 'suggest me', 'give me ideas',
            'business idea', 'project idea', 'startup', 'opportunity',
            'side hustle', 'make money', 'income', 'profit', 'grossing',
            'best idea', 'new idea', 'innovation', 'creative idea',
            'money making', 'earn', 'revenue', 'passive income',
        ],
        'weight': 1.3,
    },
}

# ═══════════════════════════════════════════════════════════
# DOMAIN DETECTION
# ═══════════════════════════════════════════════════════════

DOMAIN_PATTERNS = {
    'technology': {
        'keywords': [
            'software', 'code', 'api', 'database', 'web', 'app',
            'server', 'cloud', 'ai', 'ml', 'python', 'javascript',
            'react', 'django', 'docker', 'kubernetes', 'devops',
            'frontend', 'backend', 'fullstack', 'microservice',
            'algorithm', 'data structure', 'rest', 'graphql',
        ],
        'weight': 1.0,
    },
    'business': {
        'keywords': [
            'market', 'revenue', 'strategy', 'customer', 'sales',
            'roi', 'kpi', 'profit', 'startup', 'enterprise',
            'b2b', 'b2c', 'stakeholder', 'ceo', 'management',
            'operations', 'supply chain', 'logistics',
        ],
        'weight': 1.0,
    },
    'education': {
        'keywords': [
            'learn', 'teach', 'student', 'course', 'curriculum',
            'study', 'exam', 'classroom', 'university', 'school',
            'professor', 'lecture', 'syllabus', 'pedagogy',
        ],
        'weight': 1.0,
    },
    'creative': {
        'keywords': [
            'story', 'poem', 'art', 'design', 'creative', 'fiction',
            'narrative', 'character', 'plot', 'screenplay', 'novel',
            'music', 'painting', 'illustration', 'animation',
        ],
        'weight': 1.0,
    },
    'science': {
        'keywords': [
            'research', 'experiment', 'hypothesis', 'data', 'analysis',
            'scientific', 'physics', 'chemistry', 'biology', 'math',
            'statistics', 'laboratory', 'peer review', 'journal',
        ],
        'weight': 1.0,
    },
    'marketing': {
        'keywords': [
            'brand', 'campaign', 'social media', 'seo', 'content',
            'audience', 'engagement', 'conversion', 'funnel',
            'advertising', 'copywriting', 'analytics', 'growth',
        ],
        'weight': 1.0,
    },
    'healthcare': {
        'keywords': [
            'health', 'medical', 'patient', 'treatment', 'diagnosis',
            'clinical', 'hospital', 'doctor', 'nurse', 'therapy',
            'pharmaceutical', 'disease', 'symptom', 'wellness',
        ],
        'weight': 0.8,
    },
    'legal': {
        'keywords': [
            'law', 'legal', 'contract', 'compliance', 'regulation',
            'policy', 'attorney', 'court', 'litigation', 'patent',
            'trademark', 'liability', 'jurisdiction',
        ],
        'weight': 0.8,
    },
    'finance': {
        'keywords': [
            'finance', 'investment', 'stock', 'trading', 'portfolio',
            'banking', 'loan', 'mortgage', 'insurance', 'tax',
            'accounting', 'budget', 'financial', 'crypto', 'blockchain',
        ],
        'weight': 1.0,
    },
    'data_science': {
        'keywords': [
            'data science', 'machine learning', 'deep learning',
            'neural network', 'nlp', 'computer vision', 'tensorflow',
            'pytorch', 'pandas', 'numpy', 'sklearn', 'model training',
            'feature engineering', 'classification', 'regression',
        ],
        'weight': 1.1,
    },
    'money': {
        'keywords': [
            'money', 'income', 'profit', 'revenue', 'earn', 'making money',
            'grossing', 'business', 'startup', 'side hustle', 'passive income',
            'investment', 'roi', 'wealth', 'financial', 'entrepreneur',
            'opportunity', 'market', 'customer', 'sales', 'growth',
        ],
        'weight': 1.2,
    },
}

# ═══════════════════════════════════════════════════════════
# COMPLEXITY INDICATORS
# ═══════════════════════════════════════════════════════════

COMPLEXITY_INDICATORS = {
    'high': {
        'keywords': [
            'enterprise', 'scalable', 'distributed', 'real-time',
            'high availability', 'fault tolerant', 'microservice',
            'architecture', 'system design', 'infrastructure',
            'optimization', 'concurrent', 'parallel', 'multi-threaded',
            'production-grade', 'security', 'encryption', 'authentication',
        ],
        'multi_step_patterns': [
            r'and\s+then',
            r'after\s+that',
            r'first.*then.*finally',
            r'step\s*\d',
            r'multiple',
            r'complex',
            r'advanced',
        ],
    },
    'medium': {
        'keywords': [
            'integrate', 'connect', 'implement', 'build',
            'custom', 'dynamic', 'responsive', 'interactive',
            'validation', 'error handling', 'testing',
        ],
    },
    'low': {
        'keywords': [
            'simple', 'basic', 'hello world', 'example',
            'beginner', 'quick', 'easy', 'straightforward',
            'single', 'one', 'just',
        ],
    },
}

# ═══════════════════════════════════════════════════════════
# QUALITY ELEMENT PATTERNS
# ═══════════════════════════════════════════════════════════

QUALITY_ELEMENTS = {
    'context': {
        'patterns': [
            r'\b(context|background|situation|scenario|given that|assuming)\b',
            r'\b(currently|right now|at the moment|in our case)\b',
            r'\b(working on|project|team|company|organization)\b',
        ],
        'weight': 0.15,
    },
    'constraints': {
        'patterns': [
            r'\b(must|should|limit|constraint|within|maximum|minimum|only)\b',
            r'\b(no more than|at least|between|range|restrict|exclude)\b',
            r'\b(requirement|mandatory|optional|forbidden|avoid)\b',
        ],
        'weight': 0.12,
    },
    'output_format': {
        'patterns': [
            r'\b(format|structure|list|table|json|markdown|bullet|paragraph)\b',
            r'\b(csv|xml|yaml|html|pdf|report|document|template)\b',
            r'\b(numbered|ordered|unordered|heading|section)\b',
        ],
        'weight': 0.13,
    },
    'role': {
        'patterns': [
            r'\b(act as|you are|role|persona|expert|specialist)\b',
            r'\b(pretend|imagine you|as a|behave like|simulate)\b',
        ],
        'weight': 0.10,
    },
    'examples': {
        'patterns': [
            r'\b(example|for instance|such as|like|e\.g\.|sample)\b',
            r'\b(illustration|demonstration|case|instance|model)\b',
            r'(input|output)\s*:',
            r'```',
        ],
        'weight': 0.12,
    },
    'audience': {
        'patterns': [
            r'\b(audience|reader|beginner|expert|child|professional)\b',
            r'\b(non-technical|technical|developer|manager|executive)\b',
            r'\b(5 year old|senior|junior|intermediate|advanced user)\b',
        ],
        'weight': 0.08,
    },
    'tone': {
        'patterns': [
            r'\b(tone|formal|casual|professional|friendly|serious)\b',
            r'\b(humorous|academic|conversational|authoritative)\b',
            r'\b(empathetic|neutral|persuasive|informative)\b',
        ],
        'weight': 0.08,
    },
    'scope': {
        'patterns': [
            r'\b(scope|focus on|limited to|specifically|particular)\b',
            r'\b(in-depth|high-level|overview|detailed|comprehensive)\b',
            r'\b(brief|thorough|exhaustive|concise|expanded)\b',
        ],
        'weight': 0.10,
    },
    'success_criteria': {
        'patterns': [
            r'\b(success|goal|objective|outcome|result|deliverable)\b',
            r'\b(criteria|metric|measure|standard|benchmark)\b',
            r'\b(expected|desired|ideal|perfect|acceptable)\b',
        ],
        'weight': 0.12,
    },
}

# ═══════════════════════════════════════════════════════════
# AMBIGUITY INDICATORS
# ═══════════════════════════════════════════════════════════

AMBIGUOUS_WORDS = [
    'thing', 'stuff', 'something', 'somehow', 'whatever',
    'etc', 'some', 'maybe', 'perhaps', 'kind of', 'sort of',
    'basically', 'actually', 'really', 'very', 'just',
    'nice', 'good', 'bad', 'better', 'best', 'great',
    'cool', 'awesome', 'interesting', 'important',
]

FILLER_PATTERNS = [
    r'\b(um|uh|like|you know|i mean|so basically)\b',
    r'\b(i think|i guess|i suppose|probably|possibly)\b',
    r'\b(kind of|sort of|kinda|sorta)\b',
]

# ═══════════════════════════════════════════════════════════
# ROLE TEMPLATES PER DOMAIN
# ═══════════════════════════════════════════════════════════

DOMAIN_ROLES = {
    'technology': (
        'You are a senior software architect and technology consultant '
        'with 15+ years of experience in building scalable, production-grade systems. '
        'You follow industry best practices, write clean maintainable code, '
        'and prioritize security, performance, and reliability.'
    ),
    'business': (
        'You are a seasoned business strategist and management consultant '
        'with deep expertise in market analysis, competitive strategy, '
        'and operational excellence. You provide data-driven, actionable insights.'
    ),
    'education': (
        'You are an experienced educator and instructional designer '
        'who excels at breaking down complex topics into digestible, '
        'engaging learning experiences with clear progression from fundamentals to mastery.'
    ),
    'creative': (
        'You are an award-winning creative professional with expertise in '
        'storytelling, narrative structure, and compelling content creation. '
        'You balance creativity with purpose and audience awareness.'
    ),
    'science': (
        'You are a research scientist with deep analytical expertise, '
        'rigorous methodology, and the ability to communicate complex findings '
        'clearly. You distinguish between established facts, theories, and hypotheses.'
    ),
    'marketing': (
        'You are a senior digital marketing strategist with expertise in '
        'brand development, content strategy, audience engagement, and conversion optimization. '
        'You combine creativity with data-driven decision making.'
    ),
    'healthcare': (
        'You are a healthcare information specialist who provides accurate, '
        'evidence-based health information. You always recommend consulting '
        'qualified healthcare professionals for personal medical decisions.'
    ),
    'legal': (
        'You are a legal analyst who provides well-researched legal information '
        'and analysis. You always note that your responses are informational '
        'and not legal advice, recommending consultation with qualified attorneys.'
    ),
    'finance': (
        'You are a financial analyst with expertise in investment analysis, '
        'risk assessment, and financial planning. You provide balanced perspectives '
        'and note that your analysis is informational, not financial advice.'
    ),
    'data_science': (
        'You are a senior data scientist with expertise in machine learning, '
        'statistical analysis, and data engineering. You follow reproducible '
        'research practices and explain model choices with clear reasoning.'
    ),
    'general': (
        'You are a highly knowledgeable, thorough, and precise assistant. '
        'You provide well-structured, accurate responses and clearly distinguish '
        'between facts, opinions, and uncertainties.'
    ),
}

# ═══════════════════════════════════════════════════════════
# ENHANCEMENT TEMPLATES PER INTENT
# ═══════════════════════════════════════════════════════════

ENHANCEMENT_STRUCTURES = {
    'generate': [
        'role', 'task', 'context', 'requirements',
        'output_format', 'constraints', 'quality_criteria',
    ],
    'explain': [
        'role', 'task', 'context', 'audience',
        'depth', 'output_format', 'examples_request',
    ],
    'analyze': [
        'role', 'analysis_task', 'context', 'framework',
        'data_sources', 'output_format', 'constraints',
    ],
    'code': [
        'role', 'task', 'technical_context', 'specifications',
        'code_requirements', 'constraints', 'testing', 'documentation',
    ],
    'transform': [
        'role', 'source_description', 'target_description',
        'transformation_rules', 'constraints', 'output_format',
    ],
    'summarize': [
        'role', 'content_to_summarize', 'summary_type',
        'key_focus', 'length', 'output_format',
    ],
    'fix': [
        'role', 'problem_description', 'context', 'error_details',
        'expected_behavior', 'constraints', 'output_format',
    ],
    'brainstorm': [
        'role', 'topic', 'context', 'constraints',
        'quantity', 'evaluation_criteria', 'output_format',
    ],
    'instruct': [
        'role', 'task_to_teach', 'audience', 'prerequisites',
        'depth', 'output_format', 'tips',
    ],
    'research': [
        'role', 'research_topic', 'scope', 'sources',
        'depth', 'output_format', 'citations',
    ],
    'idea': [
        'role', 'idea_topic', 'category', 'target_audience',
        'constraints', 'quantity', 'detail_level', 'evaluation_criteria',
    ],
}

# ═══════════════════════════════════════════════════════════
# PROGRAMMING LANGUAGE CONFIGS (for code validation)
# ═══════════════════════════════════════════════════════════

SUPPORTED_LANGUAGES = {
    'python': {
        'extensions': ['.py'],
        'comment': '#',
        'keywords': ['def', 'class', 'import', 'from', 'return', 'if', 'for', 'while'],
    },
    'javascript': {
        'extensions': ['.js', '.jsx', '.ts', '.tsx'],
        'comment': '//',
        'keywords': ['function', 'const', 'let', 'var', 'return', 'class', 'import', 'export'],
    },
    'java': {
        'extensions': ['.java'],
        'comment': '//',
        'keywords': ['public', 'private', 'class', 'void', 'static', 'import', 'return'],
    },
    'sql': {
        'extensions': ['.sql'],
        'comment': '--',
        'keywords': ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER'],
    },
}

# ═══════════════════════════════════════════════════════════
# VALIDATION RULES
# ═══════════════════════════════════════════════════════════

VALIDATION_RULES = {
    'min_prompt_length': 3,
    'max_prompt_length': 10000,
    'min_enhanced_length': 50,
    'max_enhanced_length': 15000,
    'min_quality_score': 0.0,
    'max_quality_score': 1.0,
    'url_pattern': r'https?://[^\s<>"{}|\\^`\[\]]+',
    'email_pattern': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'code_block_pattern': r'```[\s\S]*?```',
}
