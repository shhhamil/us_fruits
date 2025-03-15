from . import views 
from django.urls import path

urlpatterns = [
    path('shop/', views.shop, name='Shop'),
    path('auth/check-auth/',views.check_authentication, name='check_auth'),
    path('single_product/<int:product_id>/', views.single_product, name='single_product'),

]