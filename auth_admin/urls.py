from . import views
from django.urls import path

urlpatterns = [
    path('my_admin/', views.admin_login, name='Admin_Login'),
    path('logout/admin/', views.admin_logout, name='Admin_Logout'),
    path('dashbord/', views.admin_dashbord, name='Admin_Dashbord'),
    # ______________________________________________________________________________________________
    path('category', views.Category_Manegement, name='Category'),
    path('categories/add/', views.add_category, name='Add_Category'),
    path('edit-category/<int:category_id>/', views.edit_category, name='Edit_Category'),
    path('categories/delete/<int:category_id>/', views.soft_delete_category, name='Soft_Delete_Category'),
    # _________________________________________________________________________________________________
    path('products/', views.Product_Management, name='Product'),
    path('products/add/', views.add_product, name='Add_Product'),
    path('products/<int:pk>/edit/', views.edit_product, name='Edit_Product'),
    path('products/<int:pk>/', views.view_product, name='View_Product'),
    path('products/<int:pk>/soft_delete/', views.soft_delete_product, name='Soft_Delete_Product'),
    # ___________________________--___________________________________________________________
    path('users/', views.user_management, name='User_Management'),
    path('users/block/<int:user_id>/', views.block_user, name='Block_User'),
    # ____________________________________________________________---_____________________________-
    path('orders/',views.order_management, name='Order_Management'),
    path('order/<int:orderId>/update-status/',views.update_order_status, name='Change_Status'),
    path('order/details/<int:order_id>/',views.get_order_details, name='order-details'),

    path('complaint/<int:complaint_id>/', views.admin_view_complaint, name='admin_view_complaint'),
    path('complaint/<int:complaint_id>/approve/', views.approve_complaint, name='approve_complaint'),
    path('complaint/<int:complaint_id>/reject/', views.reject_complaint, name='reject_complaint'),


    # __________________________________________________________________________________________________
    path('sales/', views.sales_report, name='sales_report'),
    path('sales/export/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('sales/export/excel/', views.export_sales_excel, name='export_sales_excel'),
    path('sales/filter/<str:period>/',views.filter_sales, name='filter_sales'),
    path('sales/filter/custom/', views.filter_custom_date, name='filter_custom_date'),
    # _____________________________________________________________________________________________
    path("coupons/",views.coupon_list, name="coupon_list"),
    path("coupons/add/", views.add_coupon, name="add_coupon"),
    path('edit/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path("coupons/delete/<int:coupon_id>/", views.delete_coupon, name="delete_coupon"),
    # __________________________________________________________________________________________________
    




]
