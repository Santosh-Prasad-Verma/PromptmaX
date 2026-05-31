"""Models for PromptX."""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class PromptCategory(models.Model):
    """Categorization of prompt domains."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    default_role = models.TextField(blank=True)
    default_constraints = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Prompt Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class EnhancementRule(models.Model):
    """Configurable rules for prompt enhancement."""
    RULE_TYPES = [
        ('add_context', 'Add Context'),
        ('add_constraints', 'Add Constraints'),
        ('add_format', 'Add Format'),
        ('add_role', 'Add Role'),
        ('add_examples', 'Add Examples'),
        ('restructure', 'Restructure'),
        ('clarify', 'Clarify'),
        ('expand', 'Expand'),
    ]

    name = models.CharField(max_length=200)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPES, db_index=True)
    trigger_pattern = models.TextField(
        help_text="Regex pattern that triggers this rule"
    )
    action_template = models.TextField(
        help_text="Template for the enhancement action"
    )
    priority = models.IntegerField(default=0)
    applicable_intents = models.JSONField(
        default=list,
        help_text="List of intents this rule applies to. Empty = all."
    )
    applicable_domains = models.JSONField(
        default=list,
        help_text="List of domains this rule applies to. Empty = all."
    )
    is_active = models.BooleanField(default=True)
    success_rate = models.FloatField(default=0.0)
    usage_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-priority']

    def __str__(self):
        return f"[{self.rule_type}] {self.name}"


class PromptHistory(models.Model):
    """Complete audit trail of all enhancements."""
    LEVELS = [
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='prompt_history'
    )
    session_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Prompts
    original_prompt = models.TextField()
    enhanced_prompt = models.TextField()
    enhancement_level = models.CharField(max_length=20, choices=LEVELS)

    # Analysis results
    detected_intent = models.CharField(max_length=100)
    detected_domain = models.CharField(max_length=100)
    detected_task_type = models.CharField(max_length=100)
    complexity_level = models.CharField(max_length=50, default='medium')

    # Quality scores
    original_quality_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    enhanced_quality_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    improvement_delta = models.FloatField(default=0.0)

    # Detailed scores (stored as JSON)
    original_scores_detail = models.JSONField(default=dict)
    enhanced_scores_detail = models.JSONField(default=dict)

    # Validation results
    validation_passed = models.BooleanField(default=True)
    validation_issues = models.JSONField(default=list)
    validation_warnings = models.JSONField(default=list)

    # Metadata
    processing_time_ms = models.FloatField(default=0.0)
    enhancement_method = models.CharField(max_length=50, default='rule_based')
    pipeline_stages_completed = models.JSONField(default=list)
    rules_applied = models.JSONField(default=list)

    # Feedback
    user_rating = models.IntegerField(null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    user_feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['detected_intent', 'detected_domain']),
            models.Index(fields=['enhancement_level']),
            models.Index(fields=['user', '-created_at'], name='history_user_created_idx'),
        ]

    def __str__(self):
        return f"[{self.enhancement_level}] {self.detected_intent} - {self.id}"


class PromptTemplate(models.Model):
    """Reusable prompt templates for specific scenarios."""
    name = models.CharField(max_length=200)
    intent = models.CharField(max_length=100, db_index=True)
    domain = models.CharField(max_length=100, db_index=True)
    template_body = models.TextField()
    variables = models.JSONField(default=list)
    usage_count = models.IntegerField(default=0)
    avg_quality_improvement = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-avg_quality_improvement']
        unique_together = ['intent', 'domain', 'name']


class UserPlan(models.Model):
    """Selected account plan for a PromptmaX user."""
    PLAN_FREE = 'free'
    PLAN_PRO = 'pro'
    PLAN_PRO_PLUS = 'pro_plus'
    PLAN_CHOICES = [
        (PLAN_FREE, 'Free'),
        (PLAN_PRO, 'Pro'),
        (PLAN_PRO_PLUS, 'Pro+'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='promptmax_plan')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    price_rs = models.PositiveIntegerField(default=0)
    selected_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-selected_at']

    def __str__(self):
        return f"{self.user.email} - {self.get_plan_display()}"


class PaymentOrder(models.Model):
    """Razorpay order lifecycle for paid PromptmaX plan activation."""
    STATUS_CREATED = 'created'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_CREATED, 'Created'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promptmax_payments')
    plan = models.CharField(max_length=20, choices=UserPlan.PLAN_CHOICES)
    amount_rs = models.PositiveIntegerField()
    amount_paise = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default='INR')
    razorpay_order_id = models.CharField(max_length=120, unique=True)
    razorpay_payment_id = models.CharField(max_length=120, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_CREATED)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='payment_user_created_idx'),
            models.Index(fields=['status', '-created_at'], name='payment_status_created_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.razorpay_order_id} - {self.status}"


class PromptProject(models.Model):
    """A collection of prompts managed by a user/team."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at'], name='project_user_updated_idx'),
        ]

    def __str__(self):
        return self.name


class PromptAsset(models.Model):
    """Equivalent to a repository for a single prompt idea."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(PromptProject, on_delete=models.CASCADE, related_name='assets', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prompt_assets')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ['user', 'name']
        indexes = [
            models.Index(fields=['user', '-updated_at'], name='asset_user_updated_idx'),
            models.Index(fields=['project', '-updated_at'], name='asset_project_updated_idx'),
            models.Index(
                fields=['is_public', '-created_at'],
                name='asset_public_created_idx',
                condition=models.Q(is_public=True),
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class PromptVersion(models.Model):
    """A specific version of a prompt, similar to a Git commit."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(PromptAsset, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField(help_text="Incremental version number")
    
    # Core content
    content = models.TextField(help_text="The prompt content for this version")
    commit_message = models.CharField(max_length=255, default="Initial version")
    
    # Metadata mapped from enhancement runs
    quality_score = models.FloatField(default=0.0)
    history_reference = models.ForeignKey(
        PromptHistory, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Link to the enhancement run that generated this version"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ['asset', 'version_number']
        indexes = [
            models.Index(fields=['asset', '-version_number'], name='version_asset_number_idx'),
        ]

    def __str__(self):
        return f"{self.asset.name} - v{self.version_number}"
