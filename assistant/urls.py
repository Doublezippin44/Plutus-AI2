from django.urls import path
from assistant.views import settings_view, FinancialAdvisorView, RegisterView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

urlpatterns = [
    path('', login_required(TemplateView.as_view(template_name='assistant/plutus.html')), name='home'),
    path('api/assistant/chat/', FinancialAdvisorView.as_view(), name='chat_api'),
    path('login/', LoginView.as_view(template_name='assistant/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('settings/', login_required(settings_view), name='settings'),
]