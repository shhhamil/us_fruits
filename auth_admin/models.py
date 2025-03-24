from django.db import models
from django.utils import timezone
from PIL import Image
from django.utils.timezone import now
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.auth.models import AbstractUser
from django.db.models import F, Sum
from django.utils.translation import gettext_lazy as _
import os 
from django.core.exceptions import ValidationError
from user_profile.models import Address
# ==================================== Custom User Model===================================================================
class CustomUser(AbstractUser):
    first_name = None
    last_name = None
    last_login = None
    is_staff = models.BooleanField(default=False)  
    email = models.EmailField(unique=True)  
    deleted_at = models.DateTimeField(null=True, blank=True)  

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs) 

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

    def restore(self):
        self.deleted_at = None
        self.is_active = True
        self.save()

# ==================== Category Model ===================================================================================
class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for product in self.products.all():
            product.save()   

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

# ==================== Product Model ==================================================================================
class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    description = models.TextField(blank=True, null=True)
    photo_1 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo_2 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo_3 = models.ImageField(upload_to='products/', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.offer_percentage < 0 or self.offer_percentage > 100:
            raise ValidationError({"offer_percentage": "Offer percentage must be between 0 and 100."})

    def save(self, *args, **kwargs):
        self.clean()
        self.calculate_offer_price()
        super().save(*args, **kwargs)
        
        self.resize_images()

    def calculate_offer_price(self):
        category_discount = self.category.discount_percentage if self.category else 0
        product_discount = self.offer_percentage
        highest_discount = max(category_discount, product_discount)  
        if highest_discount > 0:
            self.offer_price = round(self.price - (self.price * highest_discount / 100), 2)
        else:
            self.offer_price = self.price

    def resize_images(self):
        for image_field in [self.photo_1, self.photo_2, self.photo_3]:
            if image_field:
                self._resize_image(image_field)

    def _resize_image(self, image_field):
        try:
            image = Image.open(image_field)
            image = image.convert("RGB")
            image.thumbnail((500, 500), Image.Resampling.LANCZOS)

            width, height = image.size
            left = (width - 500) / 2
            top = (height - 500) / 2
            right = (width + 500) / 2
            bottom = (height + 500) / 2
            image = image.crop((left, top, right, bottom))

            image_io = BytesIO()
            image.save(image_io, format='JPEG')

            filename = os.path.basename(image_field.name)
            image_field.save(f'products/{filename}', ContentFile(image_io.getvalue()), save=False)
        except Exception as e:
            print(f"Error resizing image {image_field.name}: {e}")

    def soft_delete(self):
        self.is_active = False
        self.save()

    def restore(self):
        self.is_active = True
        self.save()

    def reduce_stock(self, quantity):
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
        else:
            raise ValueError("Not enough stock available.")

    def increase_stock(self, quantity):
        self.stock += quantity
        self.save()

    def get_photos(self):
        return [photo for photo in [self.photo_1, self.photo_2, self.photo_3] if photo]

    def __str__(self):
        return f"{self.name} ({self.category.name}) - ₹{self.offer_price}"

# =================================Order Views=====================================================================
class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SHIPPED = 'shipped'
    STATUS_CANCELLED = 'cancelled'
    STATUS_DELIVERED = 'delivered'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_SHIPPED, _('Shipped')),
        (STATUS_CANCELLED, _('Cancelled')),
        (STATUS_DELIVERED, _('Delivered')),
    ]

    PAYMENT_PAID = 'paid'
    PAYMENT_UNPAID = 'unpaid'

    PAYMENT_CHOICES = [
        (PAYMENT_PAID, _('Paid')),
        (PAYMENT_UNPAID, _('Unpaid')),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cod', _('Cash on Delivery')),
        ('razorpay', _('Razorpay')),
        ('wallet', _('Wallet')),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="orders")
    date_of_order = models.DateTimeField(auto_now_add=True)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True) 
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=30.00)   
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_UNPAID)
    cancellation_reason = models.CharField(max_length=255, blank=True, null=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)   

    def __str__(self):
        return f"Order {self.id} - {self.user.email} ({self.status}) - ({self.payment_status}) - ({self.payment_method})"

    def calculate_total(self):
        total = sum(item.get_total_offer_price for item in self.items.all())

        discount = 0
        if self.coupon and self.coupon.is_active and self.coupon.valid_from <= now() <= self.coupon.valid_to:
            discount = (total * self.coupon.discount) / 100 if self.coupon.discount else 0

        self.discount_amount = discount
        self.total = total + self.shipping_cost - discount
        self.save()

# ======================================Order Items =============================================================

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")   
    product = models.ForeignKey('Product', on_delete=models.PROTECT)    
    quantity = models.PositiveIntegerField(default=1)     
    price = models.DecimalField(max_digits=10, decimal_places=2)  

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (₹{self.price}) in Order {self.order.id}"

    @property
    def get_total_offer_price(self):
        product_offer_price = self.product.price   

        if self.product.offer_price:
            product_offer_price = self.product.offer_price

        if self.product.category and self.product.category.offer_price:
            category_offer_price = self.product.category.offer_price
            product_offer_price = min(product_offer_price, category_offer_price)

        return product_offer_price * self.quantity
# -------------------------------------------------------------------------------------------
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)  
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)  
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    usage_limit = models.PositiveIntegerField(default=1)   
    start_date = models.DateTimeField(default=now)  
    end_date = models.DateTimeField() 
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.discount_amount}%"

    def toggle_delete(self):
        self.is_deleted = not self.is_deleted
        self.save()