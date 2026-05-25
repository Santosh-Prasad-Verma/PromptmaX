from django.core.management.base import BaseCommand
from enhancer.models import PromptCategory, EnhancementRule, PromptTemplate


class Command(BaseCommand):
    help = 'Seed database with default prompt categories, rules, and templates'

    def handle(self, *args, **options):
        self._seed_categories()
        self._seed_rules()
        self._seed_templates()
        self.stdout.write(self.style.SUCCESS('Seed data loaded successfully'))

    def _seed_categories(self):
        categories = [
            {'name': 'code', 'description': 'Programming, debugging, and software development prompts',
             'default_role': 'You are an expert software engineer', 'default_constraints': ['use best practices', 'include error handling']},
            {'name': 'content', 'description': 'Blog posts, articles, and content creation',
             'default_role': 'You are a professional content writer', 'default_constraints': ['SEO optimized', 'engaging tone']},
            {'name': 'business', 'description': 'Business proposals, marketing, and strategy',
             'default_role': 'You are a senior business consultant', 'default_constraints': ['data-driven', 'actionable insights']},
            {'name': 'academic', 'description': 'Research papers, essays, and academic writing',
             'default_role': 'You are an academic researcher', 'default_constraints': ['cite sources', 'formal tone']},
            {'name': 'creative', 'description': 'Stories, scripts, and creative projects',
             'default_role': 'You are a creative writer', 'default_constraints': ['original', 'vivid descriptions']},
            {'name': 'data', 'description': 'Data analysis, ML, and statistics',
             'default_role': 'You are a data scientist', 'default_constraints': ['use statistical methods', 'explain reasoning']},
            {'name': 'general', 'description': 'General-purpose prompts and questions',
             'default_role': 'You are a knowledgeable AI assistant', 'default_constraints': ['clear', 'concise']},
        ]
        for cat in categories:
            PromptCategory.objects.get_or_create(name=cat['name'], defaults=cat)
        self.stdout.write(f'  Seeded {len(categories)} prompt categories')

    def _seed_rules(self):
        rules = [
            {'name': 'Add missing context section', 'rule_type': 'add_context',
             'trigger_pattern': r'\b(write|create|build|make)\b',
             'action_template': 'Please provide background context about the purpose and goals.', 'priority': 10},
            {'name': 'Add output format instruction', 'rule_type': 'add_format',
             'trigger_pattern': r'\b(write|create|generate|produce)\b',
             'action_template': 'Specify the desired output format (e.g., markdown, JSON, bullet points).', 'priority': 9},
            {'name': 'Add role/framework', 'rule_type': 'add_role',
             'trigger_pattern': r'\b(explain|teach|guide|help)\b',
             'action_template': 'Define the expert role or framework you want the AI to adopt.', 'priority': 8},
            {'name': 'Add constraints', 'rule_type': 'add_constraints',
             'trigger_pattern': r'\b(deploy|launch|production|scale)\b',
             'action_template': 'Include security, performance, and maintainability constraints.', 'priority': 7},
        ]
        for rule in rules:
            EnhancementRule.objects.get_or_create(name=rule['name'], defaults=rule)
        self.stdout.write(f'  Seeded {len(rules)} enhancement rules')

    def _seed_templates(self):
        templates = [
            {'name': 'Code Review', 'intent': 'code', 'domain': 'general',
             'template_body': 'Review the following code for bugs, performance issues, and style improvements.', 'variables': ['language', 'code']},
            {'name': 'Blog Post Outline', 'intent': 'content', 'domain': 'blog',
             'template_body': 'Create an outline for a blog post about {topic}. Include: title, sections, key points, and a call to action.', 'variables': ['topic']},
            {'name': 'Business Proposal', 'intent': 'business', 'domain': 'general',
             'template_body': 'Write a business proposal for {project}. Include: executive summary, problem statement, solution, timeline, and budget estimate.', 'variables': ['project']},
        ]
        for tmpl in templates:
            PromptTemplate.objects.get_or_create(
                intent=tmpl['intent'], domain=tmpl['domain'], name=tmpl['name'],
                defaults=tmpl,
            )
        self.stdout.write(f'  Seeded {len(templates)} prompt templates')
