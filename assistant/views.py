from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.shortcuts import render, redirect
from .models import ChatMessage, UserProfile # Ensure UserProfile is imported
from .openai_client import ask_openai
import yfinance as yf

class FinancialAdvisorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get("message", "")
        if not user_message:
            return Response({"error": "Message required"}, status=status.HTTP_400_BAD_REQUEST)

        # Safer way to get or create the profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_currency = profile.currency

        chart_data = None
        injected_context = f" [System note: User currency preference is {user_currency}.]"
        ticker_symbol = None
        msg_lower = user_message.lower()
        
        stock_map = {
            "nifty": "^NSEI", "tata": "TITAN.NS", "titan": "TITAN.NS", 
            "apple": "AAPL", "aapl": "AAPL", "nvidia": "NVDA", "nvda": "NVDA", 
            "tesla": "TSLA", "tsla": "TSLA", "microsoft": "MSFT", "msft": "MSFT", 
            "amazon": "AMZN", "amzn": "AMZN", "google": "GOOGL", "googl": "GOOGL", 
            "meta": "META", "facebook": "META"
        }

        for key, symbol in stock_map.items():
            if key in msg_lower:
                ticker_symbol = symbol
                break

        if ticker_symbol:
            try:
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="1mo")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    injected_context += f" Live price: {current_price:.2f} {user_currency}."
                    chart_data = {"labels": hist.index.strftime('%Y-%m-%d').tolist(), "prices": hist['Close'].tolist(), "ticker": ticker_symbol}
            except Exception:
                pass

        combined_prompt = user_message + injected_context
        ai_response = ask_openai(combined_prompt, user_currency=user_currency)

        ChatMessage.objects.create(user=request.user, role="user", content=user_message)
        ChatMessage.objects.create(user=request.user, role="assistant", content=ai_response)

        return Response({"response": ai_response, "chart_data": chart_data}, status=status.HTTP_200_OK)

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'assistant/register.html'
    success_url = reverse_lazy('login')

def settings_view(request):
    # Fetch profile, create if it doesn't exist
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile.currency = request.POST.get('currency')
        profile.save() 
        return redirect('settings') # Reload to show the updated value
        
    return render(request, 'assistant/settings.html', {'currency': profile.currency})