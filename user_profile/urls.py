from . import views 
from django.urls import path

urlpatterns = [
    path('profile/', views.profile, name='Profile'),
    path('Change-Password/', views.change_password, name='Change_Password'),
    # _______________________________________________________________________________
    path("addresses/", views.list_address, name="List_Address"),
    path("addresses/add/", views.add_address, name="Add_Address"),
    path("addresses/edit/<int:address_id>/", views.edit_address, name="Edit_Address"),
    path("addresses/delete/<int:address_id>/", views.delete_address, name="Delete_Address"),
    path('set-default/<int:address_id>/', views.set_default_address, name='Set_Default_Address'),
    # -----------------------------------------------------------------------------------------------------
    path('order-history/', views.order_history, name='Order-history'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('invoice/<int:order_id>/', views.generate_invoice, name='generate_invoice'),
# --------------------------------------------------------------------------------------
    path('wallet/', views.wallet, name='wallet'),
    path("wallet/add-money/", views.add_money, name="add_money"),





]