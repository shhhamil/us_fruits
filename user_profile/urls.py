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
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),
   path('cancel_order_item/<int:item_id>/', views.cancel_order_item, name='cancel_order_item'),
    path('orders/<int:order_id>/view/', views.order_detail, name='order_detail'),
    path('invoice/<int:order_id>/', views.generate_invoice, name='generate_invoice'),
# --------------------------------------------------------------------------------------
    path('wallet/', views.wallet, name='wallet'),
    path("add-money/<int:amount>/", views.add_money, name="add_money"),
    path("payment-success/", views.payment_success, name="payment_success"),
    # --------------------------------------------------------------------------------
    path("complaints/submit/<int:order_id>/<int:item_id>/", views.submit_complaint, name="submit_complaint"),
    path('complete-payment/', views.complete_payment, name='complete_payment'),


    






]