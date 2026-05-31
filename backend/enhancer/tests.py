"""Tests for PromptX."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .core.pipeline import PromptXPipeline
from .core.analyzer import PromptAnalyzer
from .core.quality_scorer import QualityScorer
from .core.validator import PromptValidator
from .core.fact_checker import FactChecker
from .core.intent_classifier import IntentClassifier
from .core.complexity_assessor import ComplexityAssessor


class IntentClassifierTests(TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()

    def test_code_intent(self):
        result = self.classifier.classify("Write a Python function to sort a list")
        self.assertEqual(result.primary_intent, 'code')

    def test_explain_intent(self):
        result = self.classifier.classify("Explain how neural networks work")
        self.assertEqual(result.primary_intent, 'explain')

    def test_analyze_intent(self):
        result = self.classifier.classify("Analyze this data and find trends")
        self.assertEqual(result.primary_intent, 'analyze')

    def test_fix_intent(self):
        result = self.classifier.classify("Fix this error in my code")
        self.assertEqual(result.primary_intent, 'fix')

    def test_generate_intent(self):
        result = self.classifier.classify("Create a marketing email for our new product launch")
        self.assertEqual(result.primary_intent, 'generate')

    def test_domain_detection(self):
        result = self.classifier.classify("Build a REST API with Django and PostgreSQL")
        self.assertEqual(result.domain, 'technology')

    def test_confidence_score(self):
        result = self.classifier.classify("Write a detailed Python function")
        self.assertGreater(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_multi_intent(self):
        result = self.classifier.classify(
            "Write code to analyze data and then explain the results"
        )
        self.assertTrue(len(result.secondary_intents) > 0)


class QualityScorerTests(TestCase):
    def setUp(self):
        self.scorer = QualityScorer()

    def test_low_quality_prompt(self):
        score = self.scorer.score("sort list")
        self.assertLess(score.overall, 0.5)
        self.assertEqual(score.grade, 'F')

    def test_high_quality_prompt(self):
        prompt = (
            "Act as a senior Python developer. Write a function that implements "
            "merge sort algorithm. The function should:\n"
            "- Handle edge cases like empty lists\n"
            "- Include type hints\n"
            "- Have comprehensive docstrings\n"
            "- Follow PEP 8 style\n\n"
            "Format: Provide complete Python code with usage examples.\n"
            "Constraints: Use only standard library. Target audience: intermediate developers."
        )
        score = self.scorer.score(prompt)
        self.assertGreater(score.overall, 0.5)
        self.assertIn(score.grade, ['A+', 'A', 'B'])

    def test_all_dimensions_scored(self):
        score = self.scorer.score("Explain machine learning basics")
        self.assertIn('clarity', score.detail_scores)
        self.assertIn('specificity', score.detail_scores)
        self.assertIn('completeness', score.detail_scores)
        self.assertIn('structure', score.detail_scores)
        self.assertIn('actionability', score.detail_scores)
        self.assertIn('grammar', score.detail_scores)

    def test_missing_elements_detected(self):
        score = self.scorer.score("write code")
        self.assertTrue(len(score.missing_elements) > 0)

    def test_scores_between_0_and_1(self):
        score = self.scorer.score("anything at all")
        self.assertGreaterEqual(score.overall, 0.0)
        self.assertLessEqual(score.overall, 1.0)
        for dim_score in score.detail_scores.values():
            self.assertGreaterEqual(dim_score, 0.0)
            self.assertLessEqual(dim_score, 1.0)


class ComplexityAssessorTests(TestCase):
    def setUp(self):
        self.assessor = ComplexityAssessor()

    def test_simple_task(self):
        result = self.assessor.assess("Write a simple hello world program", 'code', 'technology')
        self.assertIn(result.level, ['low', 'medium'])

    def test_complex_task(self):
        result = self.assessor.assess(
            "Design a distributed microservice architecture with real-time "
            "data processing, fault tolerance, horizontal scaling, "
            "and implement authentication with OAuth2",
            'code', 'technology'
        )
        self.assertIn(result.level, ['high', 'expert'])

    def test_decomposition(self):
        result = self.assessor.assess(
            "First build the database schema, then create the API endpoints, "
            "after that implement authentication, and finally add testing",
            'code', 'technology'
        )
        if result.requires_decomposition:
            self.assertTrue(len(result.sub_tasks) > 0)


class ValidatorTests(TestCase):
    def setUp(self):
        self.validator = PromptValidator()

    def test_valid_prompt(self):
        result = self.validator.validate("Write a Python function to sort a list")
        self.assertTrue(result.is_valid)

    def test_empty_prompt(self):
        result = self.validator.validate("")
        self.assertFalse(result.is_valid)

    def test_special_chars_only(self):
        result = self.validator.validate("!@#$%^&*()")
        self.assertFalse(result.is_valid)

    def test_unmatched_code_fences(self):
        result = self.validator.validate("Here is code ```python\nprint('hi')")
        # Should detect unmatched fence
        all_issues = result.issues + result.warnings
        has_fence_issue = any(
            'code' in i.category.lower() or 'fence' in i.message.lower()
            for i in all_issues
        )
        self.assertTrue(has_fence_issue)

    def test_contradictory_prompt(self):
        result = self.validator.validate(
            "Write a short response. Make it very comprehensive and detailed."
        )
        # Should detect contradiction
        all_warnings = result.warnings
        has_contradiction = any(
            'contradict' in w.message.lower() or 'contradict' in w.category.lower()
            for w in all_warnings
        )
        self.assertTrue(has_contradiction)


class FactCheckerTests(TestCase):
    def setUp(self):
        self.checker = FactChecker()

    def test_valid_python_version(self):
        result = self.checker.check("Using Python 3.12 for this project")
        python_items = [i for i in result.items if 'python' in i.claim.lower()]
        if python_items:
            self.assertEqual(python_items[0].status, 'verified')

    def test_deprecated_tech(self):
        result = self.checker.check("Build this using Python 2 and AngularJS")
        suspicious = [i for i in result.items if i.status == 'suspicious']
        self.assertTrue(len(suspicious) > 0)

    def test_percentage_over_100(self):
        result = self.checker.check("This will improve performance by 250%")
        suspicious = [i for i in result.items if i.status == 'suspicious']
        self.assertTrue(len(suspicious) > 0)


class PipelineTests(TestCase):
    def setUp(self):
        self.pipeline = PromptXPipeline()

    def test_basic_enhancement(self):
        result = self.pipeline.execute("sort list python", "basic")
        self.assertTrue(result.success)
        self.assertGreater(len(result.enhanced_prompt), len(result.original_prompt))

    def test_intermediate_enhancement(self):
        result = self.pipeline.execute("write a REST API in Django", "intermediate")
        self.assertTrue(result.success)
        self.assertIn('##', result.enhanced_prompt)

    def test_advanced_enhancement(self):
        result = self.pipeline.execute("analyze market data", "advanced")
        self.assertTrue(result.success)
        self.assertIn('Quality Checklist', result.enhanced_prompt)

    def test_quality_improvement(self):
        result = self.pipeline.execute("write code for login system", "intermediate")
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.improvement, 0)
        self.assertGreater(result.enhanced_quality, result.original_quality)

    def test_pipeline_stages_completed(self):
        result = self.pipeline.execute("explain recursion", "intermediate")
        self.assertTrue(result.success)
        self.assertIn('deep_analysis', result.pipeline_stages)
        self.assertIn('context_building', result.pipeline_stages)
        self.assertIn('template_rendering', result.pipeline_stages)

    def test_processing_time_recorded(self):
        result = self.pipeline.execute("hello world python", "basic")
        self.assertGreater(result.processing_time_ms, 0)

    def test_intent_detected(self):
        result = self.pipeline.execute("Explain how machine learning works", "basic")
        self.assertEqual(result.intent, 'explain')

    def test_domain_detected(self):
        result = self.pipeline.execute("Build a Django REST API with PostgreSQL", "basic")
        self.assertEqual(result.domain, 'technology')

    def test_code_language_detected(self):
        result = self.pipeline.execute("Write a Python Flask web application", "basic")
        self.assertEqual(result.programming_language, 'python')

    def test_very_short_prompt_fails(self):
        result = self.pipeline.execute("", "basic")
        self.assertFalse(result.success)

    def test_complex_prompt(self):
        prompt = (
            "Design and implement a real-time chat application using Django Channels "
            "and WebSockets. The application should support multiple chat rooms, "
            "user authentication, message persistence with PostgreSQL, "
            "and deploy with Docker. Include comprehensive tests and CI/CD pipeline."
        )
        result = self.pipeline.execute(prompt, "expert")
        self.assertTrue(result.success)
        self.assertIn(result.complexity, ['high', 'expert'])


class APIEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_enhance_endpoint(self):
        response = self.client.post('/api/v1/enhance/', {
            'prompt': 'write python code for web scraping',
            'enhancement_level': 'intermediate',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('enhanced_prompt', response.data)
        self.assertIn('original_quality', response.data)
        self.assertIn('enhanced_quality', response.data)

    def test_analyze_endpoint(self):
        response = self.client.post('/api/v1/analyze/', {
            'prompt': 'Explain machine learning to a beginner',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('intent', response.data)
        self.assertIn('quality', response.data)
        self.assertIn('complexity', response.data)

    def test_validate_endpoint(self):
        response = self.client.post('/api/v1/validate/', {
            'prompt': 'Write code using Python 3.12 and Django 5.0',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('validation', response.data)
        self.assertIn('fact_check', response.data)

    def test_compare_endpoint(self):
        response = self.client.post('/api/v1/compare/', {
            'prompt_a': 'sort list',
            'prompt_b': (
                'Write a Python function that implements merge sort '
                'with O(n log n) complexity, including type hints and docstrings'
            ),
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comparison']['winner'], 'prompt_b')

    def test_batch_enhance_endpoint(self):
        response = self.client.post('/api/v1/batch-enhance/', {
            'prompts': [
                'sort a list in python',
                'explain docker',
                'write an email to client',
            ],
            'enhancement_level': 'basic',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['total'], 3)


class SupabaseJWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.secret = 'test-supabase-jwt-secret-very-long-and-secure-123456789'
        
    @override_settings(SUPABASE_JWT_SECRET='test-supabase-jwt-secret-very-long-and-secure-123456789')
    def test_supabase_authentication_success_and_provision(self):
        import jwt
        from django.contrib.auth.models import User
        from django.test import override_settings

        # 1. Create a mock Supabase payload
        payload = {
            'sub': '550e8400-e29b-41d4-a716-446655440000',
            'email': 'supabase.test.user@example.com',
            'aud': 'authenticated',
            'user_metadata': {
                'full_name': 'Test Supabase User'
            }
        }
        
        # 2. Sign the token with our test secret
        token = jwt.encode(payload, self.secret, algorithm='HS256')
        
        # Verify user does not exist in Django yet
        self.assertFalse(User.objects.filter(email='supabase.test.user@example.com').exists())
        
        # 3. Call the Enhance endpoint with Bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post('/api/v1/enhance/', {
            'prompt': 'verify supabase auth integration',
            'enhancement_level': 'basic'
        }, format='json')
        
        # 4. Assert response is 200 OK and user was provisioned
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='supabase.test.user@example.com').exists())
        
        user = User.objects.get(email='supabase.test.user@example.com')
        self.assertEqual(user.first_name, 'Test Supabase User')
        
        # Verify unusable password is set for safety
        self.assertFalse(user.has_usable_password())

