from django.db import models
from django.contrib.auth.models import User

class FinancialProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    risk_tolerance = models.CharField(max_length=50, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')])
    financial_goals = models.TextField()
    annual_income = models.DecimalField(decimal_places=2, max_digits=12)

    def __str__(self):
        return f"{self.user.username}"

class PortfolioItem(models.Model):
    profile = models.ForeignKey(FinancialProfile, on_delete=models.CASCADE, related_name='portfolio_items')
    asset_name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=50)
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.asset_name}"

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"