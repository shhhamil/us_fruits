from . import views 
from django.urls import path

urlpatterns = [
    path("wishlist/",views. wishlist_view, name="Wishlist"),
    path("toggle/", views.toggle_wishlist, name="toggle_wishlist"),  
    path("remove/<int:item_id>/",views.remove_from_wishlist, name="remove_from_wishlist"),  
    path("check/<int:product_id>/", views.check_wishlist, name="check_wishlist"),  
]