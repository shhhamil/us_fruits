from django.urls import path
from . import views

urlpatterns = [
    #------------------------CART URL ---------------------------------------- 
    path('cart/', views.cart, name='Cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
# -----------------------------ADD ADDRESS URL --------------------------------
    path('checkout/add-address/', views.add_address_checkout, name='add_address_checkout'),
# ----------------------------CHECKOUT URL ------------------------------------ 
    path('checkout/process/', views.process_checkout, name='checkout_checkout'),
    path('checkout', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
# ------------------------------------------------------------------------------
    path("create-order/", views.create_order, name="create_order"),
    path("place_order_with_wallet/<int:order_id>/", views.place_order_with_wallet, name="place_order_with_wallet"),
    # ------------------------------------------------------------------------------
    path('apply_coupon/', views.apply_coupon, name='apply_coupon'), 

]

            