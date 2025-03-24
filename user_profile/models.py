from django.db import models
from django.utils import timezone
# ---------------------------------------------------------------------------
class Address(models.Model):
    user = models.ForeignKey('auth_admin.CustomUser', on_delete=models.CASCADE)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    update_at = models.DateTimeField(default=timezone.now)
    is_default = models.BooleanField(default=False)  

    def __str__(self):
        return f"{self.street}, {self.city}, {self.country} ({'Default' if self.is_default else 'Other'})"
    # --------------------------=-------------------------------------
class Wallet(models.Model):
    user = models.ForeignKey('auth_admin.CustomUser', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def deposit(self, amount):
        self.balance += amount
        self.save()

        transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type="credit",
            amount=amount
        )
        


    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            
            WalletTransaction.objects.create(
                wallet=self,
                transaction_type="debit",
                amount=amount
            )
            return True
        return False

# ------------------------------------------------------
class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    TRANSACTION_TYPES = [
        ("credit", "credit"),
        ("debit", "debit"),
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type} ₹{self.amount}"

 