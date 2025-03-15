from . import views 
from django.urls import path

urlpatterns = [
    path('',views.Home,name = "Home"),
    path('main_login/', views.Main_Login, name='Main_Login'),
    path('logoutuser/',views.Main_Logout,name = "Main_Logout"),
    path('signup/',views.signup,name='SignUp'),
    path('otp/',views.otp,name='Otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    # ------------------------------------------------------------------------
    path('forgot-password/',views.forgot_password,name="ForgotPassword"),
    path('reset-password/', views.reset_password, name='ResetPassword'),
    # ------------------------------------------------------------------
    path('error/', views.error, name='Error'),

]