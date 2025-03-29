# -------------------------------------------Imported items --------------------------------------------------
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate,login,logout
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import re
from django.conf import settings
from django.core.paginator import Paginator
from auth_admin.models import Product
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_datetime
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now
from datetime import timedelta
import random
from django.core.mail import send_mail
from django.conf import settings
from user_profile.models import Wallet
from django.contrib import messages
User = get_user_model()
#-------------------------------------------- Home page-------------------------------------------------------
@never_cache
def Home(request):    
    products = Product.objects.filter(is_active=True).order_by('name')
    for product in products:
        product.max_discount = max(product.offer_percentage, product.category.discount_percentage)
    offer_price = [p for p in products if p.offer_price <= 111]
    paginator = Paginator(offer_price, 6)  
    page_number = request.GET.get('page', 1)  
    products = paginator.get_page(page_number)

    context = {'products': products}  
    return render(request, 'auth_user/home.html', context)
#--------------------------------------------Main_Login-------------------------------------------------------
@never_cache
def Main_Login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
   
        if user is not None and not user.is_superuser:
            if not user.is_active:
                messages.error(request, "You're blocked. Please contact support.")
                return redirect('Main_Login')
            else:
                login(request, user)
                Wallet.objects.get_or_create(user=user)

                return redirect('Home')
        else:
            messages.error(request, 'Invalid user credentials')
            return redirect('Main_Login')
    
    return render(request, 'auth_user/main_login.html')
#------------------------------------------SIGNUP VIWES-------------------------------------------------------
@never_cache
def signup(request):
    if request.user.is_authenticated:
        return redirect('Home')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if len(password1) < 5:
            messages.error(request, 'Password must be at least 5 characters long.')
            return render(request, 'auth_user/signup.html')
        if password1 != password2:
            messages.error(request, 'Your passwords do not match.')
            return render(request, 'auth_user/signup.html')

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, 'Enter a valid email address.')
            return render(request, 'auth_user/signup.html')
        if get_user_model().objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered.')
            return render(request, 'auth_user/signup.html')

        otp = random.randint(100000, 999999)
        request.session['otp'] = otp
        request.session['name'] = username  #it use for storing (until the OTP is verified or session expires) ensuring that no data is lost if the page is reloaded.
        request.session['email'] = email
        request.session['password'] = password1
        request.session['otp_expiry'] = timezone.now() + timedelta(minutes=10) 
        request.session['otp_expiry'] = request.session['otp_expiry'].isoformat()
        request.session['otp_type'] = 'signup'

        send_mail('Your OTP for Account Verification',f'Your OTP is: {otp}',settings.EMAIL_HOST_USER,[email],fail_silently=False,)

        print(f'this otp for the signup varification :  {otp}')

        messages.success(request, 'An OTP has been sent to your email. Please verify to complete registration.')
        return redirect('Otp')
    return render(request, 'auth_user/signup.html')
# ----------------------------------------------otp-----------------------------------------------------------
@never_cache
def otp(request):
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        otp_type = request.session.get('otp_type') 

        if otp_type == 'forgot_password':
            stored_otp = request.session.get('reset_otp')
            otp_expiry_str = request.session.get('reset_otp_expiry')
        else:
            stored_otp = request.session.get('otp')
            otp_expiry_str = request.session.get('otp_expiry')

        if not otp_expiry_str:
            messages.error(request, "OTP expired. Please request OTP again.")
            return redirect('ForgotPassword' if otp_type == 'forgot_password' else 'SignUp')

        otp_expiry = parse_datetime(otp_expiry_str)

        if str(stored_otp) == str(otp_entered) and now() < otp_expiry:
            if otp_type == 'forgot_password':
                return redirect('ResetPassword') 
            else:
                username = request.session.get('name')
                email = request.session.get('email')
                password = request.session.get('password')

                if not all([username, email, password]):
                    messages.error(request, "Session expired or invalid data. Please sign up again.")
                    return redirect('SignUp')

                User = get_user_model()
                user = User.objects.filter(email=email).first()
                if user:
                    messages.warning(request, "User already exists. Logging in...")
                else:
                    user = User(email=email)
                    user.set_password(password)
                    user.save()
                    messages.success(request, "Your account has been created successfully.")

                login(request, user, backend='allauth.account.auth_backends.AuthenticationBackend')
                request.session.flush()

                return redirect('Main_Login')
        else:
            messages.error(request, "Invalid or expired OTP. Please try again.")
            return redirect('Otp')

    return render(request, 'auth_user/otp.html')
# ----------------------------------------------resent otp----------------------------------------------------
@never_cache
def resend_otp(request):
    otp_type = request.session.get('otp_type') 
    if otp_type == 'forgot_password':
        email = request.session.get('reset_email')
        if not email:
            messages.error(request, 'No email found in session. Please try again.')
            return redirect('ForgotPassword')

        otp = random.randint(100000, 999999)
        otp_expiry = now() + timedelta(minutes=10)

        request.session['reset_otp'] = str(otp)
        request.session['reset_otp_expiry'] = otp_expiry.isoformat()

        send_otp_email(email, otp) 
        messages.success(request, "A new OTP has been sent to your email.")
        return redirect('Otp') 

    elif otp_type == 'signup':
        email = request.session.get('email')
        if not email:
            messages.error(request, 'No email found in session. Please sign up again.')
            return redirect('signup')

        otp = random.randint(100000, 999999)
        otp_expiry = now() + timedelta(minutes=10)

        request.session['otp'] = str(otp)
        request.session['otp_expiry'] = otp_expiry.isoformat()

        send_mail(
            'Your OTP for Account Verification',
            f'Your new OTP is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        messages.success(request, 'A new OTP has been sent to your email.')
        return redirect('Otp') 

    else:
        messages.error(request, 'Invalid OTP request. Please try again.')
        return redirect('Home')
#-----------------------------------------------Main_logout---------------------------------------------------
@never_cache
def Main_Logout(request):
        logout(request)  
        request.session.flush()  
        return redirect('Main_Login') 
# --------------------------------------------Error page------------------------------------------------------
def error(request):
    return render(request,'auth_user/error.html')
# --------------------------------------------forgot_password-------------------------------------------------
@never_cache
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = get_user_model().objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect('ForgotPassword')

        otp = random.randint(100000, 999999)
        otp_expiry = now() + timedelta(minutes=10)

        request.session['reset_otp'] = str(otp)
        request.session['reset_email'] = email
        request.session['reset_otp_expiry'] = otp_expiry.isoformat()
        request.session['otp_type'] = 'forgot_password'

        send_otp_email(email, otp)
        print(f'this otp for the forgot password :  {otp}')
        messages.success(request, "An OTP has been sent to your email.")
        return redirect('Otp')
    return render(request, 'auth_user/forgot.html')
def send_otp_email(email, otp):
    subject = "Your Password Reset OTP"
    message = f"Your OTP for password reset is {otp}. It is valid for 10 minutes."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
# -------------------------------------------reset password---------------------------------------------------
@never_cache
def reset_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('ResetPassword')

        email = request.session.get('reset_email')
        if not email:
            messages.error(request, "Session expired. Please request OTP again.")
            return redirect('Otp')

        user = User.objects.filter(email=email).first()
        if user:
            user.password = make_password(new_password)
            user.save()
            messages.success(request, "Your password has been reset successfully.")
            request.session.flush()
            return redirect('Main_Login')

    return render(request, 'auth_user/resetpa.html')
# -------------------------------------------------------------------------------------------------------------