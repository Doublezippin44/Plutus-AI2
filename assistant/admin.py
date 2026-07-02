from django.contrib import admin
from .models import FinancialProfile, PortfolioItem, ChatMessage

admin.site.register(FinancialProfile)
admin.site.register(PortfolioItem)
admin.site.register(ChatMessage)