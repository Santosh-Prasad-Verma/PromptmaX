from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnhancePromptView,
    AnalyzePromptView,
    ValidatePromptView,
    ComparePromptsView,
    ABTestView,
    AnalyzeURLView,
    WebSearchView,
    IdeasView,
    PromptHistoryView,
    BatchEnhanceView,
    FeedbackView,
    HealthCheckView,
    PromptProjectViewSet,
    PromptAssetViewSet,
    PromptVersionViewSet,
    ExecutePromptView,
    TaskStatusView,
    MultiModelView,
)
from .views_auth import (
    RegisterView,
    VerifyOTPView,
    ResendOTPView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RazorpayCreateOrderView,
    RazorpayVerifyPaymentView,
    CurrentUserView,
    SelectPlanView,
    TokenObtainView,
)

from .views_dynamic import ExtractVariablesView

app_name = 'enhancer'

router = DefaultRouter()
router.register(r'projects', PromptProjectViewSet, basename='promptproject')
router.register(r'assets', PromptAssetViewSet, basename='promptasset')
router.register(r'versions', PromptVersionViewSet, basename='promptversion')

urlpatterns = [
    path('api/', include(router.urls)),
    path('extract-variables/', ExtractVariablesView.as_view(), name='extract-variables'),
    path('execute/', ExecutePromptView.as_view(), name='execute'),
    # Core endpoints
    path('enhance/', EnhancePromptView.as_view(), name='enhance'),
    path('analyze/', AnalyzePromptView.as_view(), name='analyze'),
    path('validate/', ValidatePromptView.as_view(), name='validate'),
    path('compare/', ComparePromptsView.as_view(), name='compare'),
    path('ab-test/', ABTestView.as_view(), name='ab-test'),
    path('multi-model/', MultiModelView.as_view(), name='multi-model'),
    path('analyze-url/', AnalyzeURLView.as_view(), name='analyze-url'),
    path('web-search/', WebSearchView.as_view(), name='web-search'),
    path('ideas/', IdeasView.as_view(), name='ideas'),
    path('history/', PromptHistoryView.as_view(), name='history'),
    path('batch-enhance/', BatchEnhanceView.as_view(), name='batch-enhance'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),
    path('health/', HealthCheckView.as_view(), name='health'),
    path('task/<str:task_id>/status/', TaskStatusView.as_view(), name='task-status'),
    path('task/<str:task_id>/status', TaskStatusView.as_view()),

    # Backward-compatible aliases for frontend JS
    path('enhance', EnhancePromptView.as_view()),
    path('quality-heatmap/', AnalyzePromptView.as_view()),
    path('quality-heatmap', AnalyzePromptView.as_view()),

    path('execute/', ExecutePromptView.as_view(), name='execute'),
    
    # Auth
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='auth-verify-otp'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='auth-resend-otp'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('auth/select-plan/', SelectPlanView.as_view(), name='auth-select-plan'),
    path('auth/razorpay/order/', RazorpayCreateOrderView.as_view(), name='auth-razorpay-order'),
    path('auth/razorpay/verify/', RazorpayVerifyPaymentView.as_view(), name='auth-razorpay-verify'),
    path('auth/token/', TokenObtainView.as_view(), name='auth-token'),
    path('auth/forgot-password/', PasswordResetRequestView.as_view(), name='auth-forgot-password'),
    path('auth/reset-password/', PasswordResetConfirmView.as_view(), name='auth-reset-password'),
]
