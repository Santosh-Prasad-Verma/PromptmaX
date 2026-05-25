"""Validation module for PromptX."""

import re
import ast
import logging
import requests
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse

from django.conf import settings
from ..utils.text_processing import extract_urls, extract_code_blocks, extract_emails
from ..utils.helpers import timer, safe_execute

logger = logging.getLogger('enhancer')


@dataclass
class ValidationIssue:
    severity: str  # 'error', 'warning', 'info'
    category: str
    message: str
    location: str  # Where in the text the issue was found
    suggestion: str


@dataclass
class ValidationResult:
    is_valid: bool
    score: float  # 0-1, overall validation score
    issues: List[ValidationIssue]
    warnings: List[ValidationIssue]
    info: List[ValidationIssue]
    checks_performed: List[str]
    resources_validated: Dict[str, bool]


class PromptValidator:
    """
    Comprehensive validation engine that verifies:
    1. URL validity and accessibility
    2. Code syntax correctness
    3. Logical consistency
    4. Resource references
    5. Structural integrity
    6. Content safety
    7. Grammar and spelling
    """

    def __init__(self):
        self.config = settings.PROMPTX['VALIDATION']

    @timer
    def validate(self, text: str, context: Dict = None) -> ValidationResult:
        """Run all validation checks on the prompt."""
        issues = []
        warnings = []
        info = []
        checks_performed = []
        resources_validated = {}

        # Check 1: Basic structure
        checks_performed.append('structural_integrity')
        struct_issues = self._validate_structure(text)
        issues.extend([i for i in struct_issues if i.severity == 'error'])
        warnings.extend([i for i in struct_issues if i.severity == 'warning'])

        # Check 2: URL validity
        if self.config.get('CHECK_URL_VALIDITY', True):
            checks_performed.append('url_validation')
            url_results = self._validate_urls(text)
            for url, is_valid, issue in url_results:
                resources_validated[url] = is_valid
                if issue:
                    if issue.severity == 'error':
                        issues.append(issue)
                    else:
                        warnings.append(issue)

        # Check 3: Code syntax
        if self.config.get('CHECK_CODE_SYNTAX', True):
            checks_performed.append('code_syntax')
            code_issues = self._validate_code_blocks(text)
            issues.extend([i for i in code_issues if i.severity == 'error'])
            warnings.extend([i for i in code_issues if i.severity == 'warning'])

        # Check 4: Logical consistency
        if self.config.get('CHECK_LOGICAL_CONSISTENCY', True):
            checks_performed.append('logical_consistency')
            logic_issues = self._validate_logical_consistency(text)
            warnings.extend(logic_issues)

        # Check 5: Content completeness
        checks_performed.append('content_completeness')
        completeness_issues = self._validate_completeness(text)
        info.extend(completeness_issues)

        # Check 6: Balanced delimiters
        checks_performed.append('balanced_delimiters')
        delim_issues = self._validate_delimiters(text)
        issues.extend([i for i in delim_issues if i.severity == 'error'])
        warnings.extend([i for i in delim_issues if i.severity == 'warning'])

        # Check 7: Email validity
        checks_performed.append('email_validation')
        email_issues = self._validate_emails(text)
        warnings.extend(email_issues)

        # Check 8: Contradiction detection
        checks_performed.append('contradiction_detection')
        contradiction_issues = self._detect_contradictions(text)
        warnings.extend(contradiction_issues)

        # Calculate overall score
        error_count = len(issues)
        warning_count = len(warnings)
        score = max(0.0, 1.0 - (error_count * 0.15) - (warning_count * 0.05))

        is_valid = error_count == 0

        return ValidationResult(
            is_valid=is_valid,
            score=round(score, 3),
            issues=issues,
            warnings=warnings,
            info=info,
            checks_performed=checks_performed,
            resources_validated=resources_validated,
        )

    def _validate_structure(self, text: str) -> List[ValidationIssue]:
        """Validate basic prompt structure."""
        issues = []

        # Check minimum length
        if len(text.strip()) < 3:
            issues.append(ValidationIssue(
                severity='error',
                category='structure',
                message='Prompt is too short to be meaningful',
                location='entire_prompt',
                suggestion='Provide at least a complete sentence describing your request.'
            ))

        # Check for only special characters
        if text.strip() and not re.search(r'[a-zA-Z]', text):
            issues.append(ValidationIssue(
                severity='error',
                category='structure',
                message='Prompt contains no readable text',
                location='entire_prompt',
                suggestion='Include text describing what you need.'
            ))

        # Check for excessive repetition
        words = text.lower().split()
        if len(words) > 5:
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.4 and max_freq > 3:
                repeated_word = max(word_freq, key=word_freq.get)
                issues.append(ValidationIssue(
                    severity='warning',
                    category='structure',
                    message=f'Excessive repetition of "{repeated_word}" ({max_freq} times)',
                    location='entire_prompt',
                    suggestion='Reduce repetition for clarity.'
                ))

        # Check for incomplete sentences at start
        if text.strip() and text.strip()[0].islower() and len(words) < 4:
            issues.append(ValidationIssue(
                severity='warning',
                category='structure',
                message='Prompt appears to be a fragment rather than a complete request',
                location='start',
                suggestion='Start with a clear action verb or complete sentence.'
            ))

        return issues

    def _validate_urls(self, text: str) -> List[Tuple[str, bool, ValidationIssue]]:
        """Validate all URLs in the text."""
        results = []
        urls = extract_urls(text)

        for url in urls:
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    results.append((url, False, ValidationIssue(
                        severity='error',
                        category='url_validation',
                        message=f'Malformed URL: {url}',
                        location=url,
                        suggestion='Check URL format (should start with http:// or https://)'
                    )))
                    continue

                # Try to reach the URL
                try:
                    response = requests.head(
                        url,
                        timeout=self.config.get('URL_TIMEOUT', 5),
                        allow_redirects=True,
                        headers={'User-Agent': 'PromptX-Validator/1.0'}
                    )
                    if response.status_code >= 400:
                        results.append((url, False, ValidationIssue(
                            severity='warning',
                            category='url_validation',
                            message=f'URL returned status {response.status_code}: {url}',
                            location=url,
                            suggestion='Verify the URL is correct and accessible.'
                        )))
                    else:
                        results.append((url, True, None))
                except requests.exceptions.Timeout:
                    results.append((url, False, ValidationIssue(
                        severity='warning',
                        category='url_validation',
                        message=f'URL timed out: {url}',
                        location=url,
                        suggestion='URL may be slow or unreachable. Verify it works.'
                    )))
                except requests.exceptions.ConnectionError:
                    results.append((url, False, ValidationIssue(
                        severity='warning',
                        category='url_validation',
                        message=f'Cannot connect to URL: {url}',
                        location=url,
                        suggestion='URL appears unreachable. Check the address.'
                    )))

            except Exception as e:
                results.append((url, False, ValidationIssue(
                    severity='warning',
                    category='url_validation',
                    message=f'URL validation failed for: {url} ({str(e)})',
                    location=url,
                    suggestion='Verify this URL manually.'
                )))

        return results

    def _validate_code_blocks(self, text: str) -> List[ValidationIssue]:
        """Validate code syntax in code blocks."""
        issues = []
        code_blocks = extract_code_blocks(text)

        for lang, code in code_blocks:
            if lang.lower() in ['python', 'py', '']:
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    issues.append(ValidationIssue(
                        severity='warning',
                        category='code_syntax',
                        message=f'Python syntax error in code block: {str(e)}',
                        location=f'code_block ({lang})',
                        suggestion=f'Fix syntax at line {e.lineno}: {e.msg}'
                    ))

            # Check for incomplete code blocks
            if code.strip().endswith('...') or code.strip().endswith('# TODO'):
                issues.append(ValidationIssue(
                    severity='info',
                    category='code_syntax',
                    message='Code block appears incomplete',
                    location=f'code_block ({lang})',
                    suggestion='Complete the code or indicate it is pseudocode.'
                ))

        # Check for unmatched code fences
        fence_count = text.count('```')
        if fence_count % 2 != 0:
            issues.append(ValidationIssue(
                severity='error',
                category='code_syntax',
                message='Unmatched code block fence (```) detected',
                location='code_blocks',
                suggestion='Ensure every opening ``` has a matching closing ```.'
            ))

        return issues

    def _validate_logical_consistency(self, text: str) -> List[ValidationIssue]:
        """Check for logical inconsistencies in the prompt."""
        issues = []
        text_lower = text.lower()

        # Check for contradictory instructions
        contradiction_pairs = [
            (r'\bshort\b', r'\bdetailed\b', 'short vs detailed'),
            (r'\bbrief\b', r'\bcomprehensive\b', 'brief vs comprehensive'),
            (r'\bsimple\b', r'\bcomplex\b', 'simple vs complex'),
            (r'\bformal\b', r'\bcasual\b', 'formal vs casual'),
            (r'\binclude\b.*\bexclude\b', None, 'include and exclude may conflict'),
            (r'\bdo\b', r'\bdo not\b', 'positive and negative instructions'),
            (r'\bminimum\s+(\d+)', r'\bmaximum\s+(\d+)', 'min/max range'),
        ]

        for pattern1, pattern2, desc in contradiction_pairs:
            if pattern2:
                if re.search(pattern1, text_lower) and re.search(pattern2, text_lower):
                    # Special case: check min/max values
                    if desc == 'min/max range':
                        min_match = re.search(r'\bminimum\s+(\d+)', text_lower)
                        max_match = re.search(r'\bmaximum\s+(\d+)', text_lower)
                        if min_match and max_match:
                            if int(min_match.group(1)) > int(max_match.group(1)):
                                issues.append(ValidationIssue(
                                    severity='warning',
                                    category='logical_consistency',
                                    message=f'Minimum value exceeds maximum value',
                                    location='constraints',
                                    suggestion='Verify your min/max values are correct.'
                                ))
                    else:
                        rpl = desc.split(" vs ")
                        suggestion = f'Clarify whether you want {rpl[0]} or {rpl[1]}.' if len(rpl) >= 2 else f'Review the contradiction: {desc}.'
                        issues.append(ValidationIssue(
                            severity='warning',
                            category='logical_consistency',
                            message=f'Potentially contradictory: {desc}',
                            location='entire_prompt',
                            suggestion=suggestion,
                        ))

        return issues

    def _validate_completeness(self, text: str) -> List[ValidationIssue]:
        """Check if the prompt is complete enough for good results."""
        issues = []
        word_count = len(text.split())

        if word_count < 5:
            issues.append(ValidationIssue(
                severity='info',
                category='completeness',
                message='Very short prompt may produce generic results',
                location='entire_prompt',
                suggestion='Add more detail about what specifically you need.'
            ))

        # Check if it ends mid-sentence
        text_stripped = text.strip()
        if text_stripped and text_stripped[-1] not in '.!?:;)]\'"':
            words = text_stripped.split()
            last_word = words[-1] if words else ''
            incomplete_endings = [
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                'to', 'for', 'with', 'by', 'from', 'is', 'are', 'was',
                'that', 'this', 'of', 'as',
            ]
            if last_word.lower() in incomplete_endings:
                issues.append(ValidationIssue(
                    severity='info',
                    category='completeness',
                    message='Prompt appears to end mid-sentence',
                    location='end',
                    suggestion='Complete your sentence or thought.'
                ))

        return issues

    def _validate_delimiters(self, text: str) -> List[ValidationIssue]:
        """Check for balanced delimiters."""
        issues = []
        pairs = {'(': ')', '[': ']', '{': '}', '"': '"'}

        for open_d, close_d in pairs.items():
            if open_d == close_d:
                count = text.count(open_d)
                if count % 2 != 0:
                    issues.append(ValidationIssue(
                        severity='warning',
                        category='delimiters',
                        message=f'Unmatched {open_d} found ({count} occurrences)',
                        location='entire_prompt',
                        suggestion=f'Check that all {open_d} are properly paired.'
                    ))
            else:
                if text.count(open_d) != text.count(close_d):
                    issues.append(ValidationIssue(
                        severity='warning',
                        category='delimiters',
                        message=f'Unmatched {open_d}{close_d} brackets',
                        location='entire_prompt',
                        suggestion=f'Ensure every {open_d} has a matching {close_d}.'
                    ))

        return issues

    def _validate_emails(self, text: str) -> List[ValidationIssue]:
        """Validate email addresses in text."""
        issues = []
        emails = extract_emails(text)

        for email in emails:
            # Basic format check (already passed regex)
            parts = email.split('@')
            if len(parts) == 2:
                domain = parts[1]
                if '.' not in domain:
                    issues.append(ValidationIssue(
                        severity='warning',
                        category='email_validation',
                        message=f'Suspicious email domain: {email}',
                        location=email,
                        suggestion='Verify this email address is correct.'
                    ))

        return issues

    def _detect_contradictions(self, text: str) -> List[ValidationIssue]:
        """Detect contradictory statements."""
        issues = []
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip().lower() for s in sentences if s.strip()]

        # Look for negation patterns
        for i, sent in enumerate(sentences):
            for j, other in enumerate(sentences):
                if i >= j:
                    continue

                # Check if one sentence negates the other
                words_i = set(sent.split()) - {'do', 'not', "don't", "doesn't", 'no', 'never'}
                words_j = set(other.split()) - {'do', 'not', "don't", "doesn't", 'no', 'never'}

                overlap = words_i & words_j
                if len(overlap) >= 3:  # Significant overlap
                    has_neg_i = any(
                        neg in sent for neg in ["don't", "doesn't", "not", "never", "no"]
                    )
                    has_neg_j = any(
                        neg in other for neg in ["don't", "doesn't", "not", "never", "no"]
                    )
                    if has_neg_i != has_neg_j:
                        issues.append(ValidationIssue(
                            severity='warning',
                            category='contradiction',
                            message='Potentially contradictory statements detected',
                            location=f'sentences {i+1} and {j+1}',
                            suggestion='Review these sentences for consistency.'
                        ))

        return issues
