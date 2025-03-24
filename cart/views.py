import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.conf import settings
import pytz
from django.utils.timezone import now, localtime
from decimal import Decimal
from django.utils import timezone
from django.db.models import F, Sum
from django.contrib import messages
from django.views.decorators.http import require_POST
from user_profile.models import Address ,Wallet ,WalletTransaction
from auth_admin.models import Product
import razorpay
from auth_admin.models import Coupon
from django.conf import settings
from cart.models import CartItem
from django.views.decorators.csrf import csrf_exempt  
from .models import Cart
import json
from auth_admin.models import OrderItem
from auth_admin.models import Order,OrderItem
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
# -------------------------------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
@login_required
def cart(request):
    if not request.user.is_authenticated:
        return redirect('Main_Login')

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('product').order_by('product__name')

    subtotal = cart_items.aggregate(
        total=Sum(
            ExpressionWrapper(
                F('quantity') * F('product__offer_price'),
                output_field=DecimalField())))['total'] or 0 

    shipping_cost = getattr(settings, 'SHIPPING_COST', 30)  
    total_price = subtotal + shipping_cost  
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,   
        'shipping_cost': shipping_cost,
        'total_price': total_price,  
    }

    return render(request, 'cart/cart.html', context)
# ---------------------------------------------------------------------------------------------------------------
@login_required
@require_POST
def add_to_cart(request, product_id):
    try:
        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(user=request.user)
            try:
                quantity = int(request.POST.get('quantity', 1))
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid quantity'}, status=400)

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)

            if quantity <= 0:
                return JsonResponse({'status': 'error', 'message': 'Quantity must be greater than 0'}, status=400)

            if quantity > product.stock:
                return JsonResponse({'status': 'error', 'message': f'Only {product.stock} items available in stock'}, status=400)

            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

            new_quantity = cart_item.quantity + quantity

            total_items_in_cart = sum(item.quantity for item in cart.cart_items.all())
            if total_items_in_cart + quantity > 5:
                return JsonResponse({'status': 'error', 'message': 'You can only order up to 5 products at a time.'}, status=400)

            cart_item.quantity = new_quantity
            cart_item.save()

            cart_count = sum(item.quantity for item in cart.cart_items.all())

            return JsonResponse({'status': 'success', 'message': 'Product added to cart successfully!', 'cart_count': cart_count})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An error occurred while adding to cart'}, status=500)
# --------------------------------------------------------------------------------------------------------------
@require_POST
@login_required
def update_cart(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        cart_item.refresh_from_db() # Refresh the cart_item from the database to get the latest quantity
        if action == 'increase':
            if cart_item.quantity >= cart_item.product.stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Sorry, only {cart_item.product.stock} items available in stock'
                }, status=400)

            if cart_item.quantity >= 5:
                return JsonResponse({
                    'success': False,
                    'message': 'Maximum quantity limit (5) reached'
                }, status=400)

            cart_item.quantity += 1

        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Minimum quantity is 1'
                }, status=400)

        cart_item.save()
        item_total = cart_item.product.offer_price * cart_item.quantity
        
        cart_total = sum(item.product.offer_price * item.quantity for item in CartItem.objects.filter(cart__user=request.user))

        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'total': float(item_total),
            'cart_total': float(cart_total)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
# --------------------------------------------------------------------------------------------------------------
@require_POST
@login_required
def remove_from_cart(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        return JsonResponse({
            'success': True,
            'message': 'Item removed successfully'
        })
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart item not found.'
        })
# ---------------------------------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
@login_required
def add_address_checkout(request):
    if request.method == "POST":
        street = request.POST.get("street", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pin_code = request.POST.get("pin_code", "").strip()
        country = request.POST.get("country", "").strip()
        phone = request.POST.get("phone", "").strip()
        is_default = request.POST.get("is_default") == "on"

        logger.debug(f"Received data: {street}, {city}, {state}, {pin_code}, {country}, {phone}, {is_default}")

        if not all([street, city, state, pin_code, country, phone]):
            return JsonResponse({"success": False, "message": "Please fill all fields."})

        if len(phone) != 10:
            return JsonResponse({"success": False, "message": "Please enter a valid 10-digit phone number."})

        try:
            with transaction.atomic():
                address = Address.objects.create(
                    user=request.user,
                    street=street,
                    city=city,
                    state=state,
                    pin_code=pin_code[:15],
                    country=country,
                    phone=phone[:10],
                    is_default=is_default,
                )

                if is_default:
                    Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)

                return JsonResponse({"success": True})
        except Exception as e:
            logger.error(f"Error while adding address: {str(e)}")
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request method."})
# ---------------------------------------------------------------------------------------------------------------
@login_required
def process_checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)   
        cart_items = CartItem.objects.filter(cart=cart)   

        if not cart_items.exists():
            messages.error(request, "Your cart is empty. Add items before proceeding to checkout.")
            return redirect('cart')  

        return redirect('checkout')   

    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty. Add items before proceeding to checkout.")
        return redirect('cart')  
# -------------------------------- CHECKOUT VIEW -------------------------------- #
@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            messages.warning(request, "Your cart is empty. Please add items before checkout.")
            return redirect("Cart")

        cart_total = sum(item.quantity * item.product.offer_price for item in cart_items)
        shipping_cost = getattr(settings, "SHIPPING_COST", 30)
        total_amount = cart_total + shipping_cost

    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty. Please add items to proceed.")
        return redirect("Cart")

    addresses = Address.objects.filter(user=request.user)
    wallet = Wallet.objects.filter(user=request.user).first()
    wallet_balance = wallet.balance if wallet else 0  
    coupons = Coupon.objects.filter(is_deleted=False)

    discount_amount = 0
    applied_coupon = None
    coupon_code = request.GET.get("coupon_code")

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_deleted=False)
            current_time = timezone.now()

            if coupon.start_date.astimezone(timezone.utc) <= current_time <= coupon.end_date.astimezone(timezone.utc):
                if total_amount >= coupon.min_order_amount:
                    discount_amount = min(coupon.discount_amount, total_amount)
                    total_amount -= discount_amount
                    applied_coupon = coupon 
                    messages.success(request, f"Coupon applied! You saved ₹{discount_amount}.")
                else:
                    messages.warning(request, f"Minimum order amount for this coupon is ₹{coupon.min_order_amount}.")
            else:
                messages.warning(request, "Invalid or expired coupon.")

        except Coupon.DoesNotExist:
            messages.warning(request, "Coupon not found.")

    request.session["applied_coupon_code"] = applied_coupon.code if applied_coupon else None
    request.session["discount_amount"] = discount_amount

    context = {
        "cart_items": cart_items,
        "cart_total": cart_total,
        "shipping_cost": shipping_cost,
        "discount_amount": discount_amount,
        "total_amount": total_amount,
        "addresses": addresses,
        "wallet_balance": wallet_balance,
        "coupons": coupons,
        "coupon_code": coupon_code
    }

    return render(request, "cart/checkout.html", context)
# -------------------------------- PLACE ORDER VIEW ----------------------------------------- -----------------#
@login_required
def place_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')
        payment_method = data.get('payment_method')
        razorpay_payment_id = data.get("razorpay_payment_id")

#this for  Retrieve applied coupon and discount from the apply coupon viwes session 
        applied_coupon_code = request.session.get("applied_coupon_code")
        discount_amount = request.session.get("discount_amount", 0)

        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        if not cart_items.exists():
            return JsonResponse({'success': False, 'message': 'Your cart is empty.'})

        cart_total = sum(item.quantity * item.product.offer_price for item in cart_items)
        shipping_cost = getattr(settings, "SHIPPING_COST", 30)

        applied_coupon = None
        if applied_coupon_code:
            try:
                applied_coupon = Coupon.objects.get(code=applied_coupon_code, is_deleted=False)
                if not (applied_coupon.start_date <= timezone.now() <= applied_coupon.end_date):
                    applied_coupon = None   
            except Coupon.DoesNotExist:
                applied_coupon = None

        total_amount = max(cart_total - Decimal(discount_amount) + shipping_cost, 0)

        if payment_method == "cod" and total_amount >= 1000:
            return JsonResponse({'success': False, 'message': 'COD is not available for orders above ₹1000.'})

        if payment_method == "razorpay":
            if not razorpay_payment_id:
                return JsonResponse({'success': False, 'message': 'Use the "Pay with Razorpay" button instead.'})
            try:
                razorpay_client.payment.fetch(razorpay_payment_id)
            except razorpay.errors.BadRequestError:
                return JsonResponse({'success': False, 'message': 'Invalid Razorpay payment ID.'})

        if payment_method == "wallet":
            user_wallet, _ = Wallet.objects.get_or_create(user=request.user)
            if user_wallet.balance < total_amount:
                return JsonResponse({'success': False, 'message': 'Insufficient wallet balance.'})

        payment_status = 'paid' if payment_method in ['razorpay', 'wallet'] else 'unpaid'

        for item in cart_items:
            if item.product.stock < item.quantity:
                return JsonResponse({'success': False, 'message': f'Not enough stock for {item.product.name}.'})

        with transaction.atomic():
            address = get_object_or_404(Address, id=address_id)

            order = Order.objects.create(
                user=request.user,
                address=address,
                total=total_amount, 
                shipping_cost=shipping_cost,
                payment_status=payment_status,
                payment_method=payment_method,
                discount_amount=discount_amount,  
                coupon=applied_coupon
            )

            if payment_method == "razorpay":
                order.razorpay_payment_id = razorpay_payment_id
                order.save()

            if payment_method == "wallet":
                user_wallet.balance -= total_amount
                user_wallet.save()
                WalletTransaction.objects.create(
                    wallet=user_wallet,
                    transaction_type="debit",
                    amount=total_amount
                )

            for item in cart_items:
                product = item.product
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.offer_price  
                )
                product.stock -= item.quantity
                product.save()


            cart_items.delete()

# it for Remove Coupon Data from Session
            request.session.pop("applied_coupon_code", None)
            request.session.pop("discount_amount", None)

        return JsonResponse({'success': True, 'redirect_url': '/order-history/'})

    except Exception as e:
        logger.error(" Order processing failed", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Something went wrong: {str(e)}'})
# ---------------------------- RAZORPAY ORDER CREATION ---------------------------- #
RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
@csrf_exempt
def create_order(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = int(float(data.get("cartTotal", 0)) * 100)   

            if amount <= 0:
                return JsonResponse({"error": "Invalid amount"}, status=400)

            order_data = {
                "amount": amount,
                "currency": "INR",
                "payment_capture": 1
            }
            razorpay_order = razorpay_client.order.create(order_data)
            return JsonResponse({
                "razorpayKeyId": settings.RAZORPAY_KEY_ID,
                "amount": razorpay_order["amount"],
                "razorpayOrderId": razorpay_order["id"]
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)
# ------------------------ PLACE ORDER WITH WALLET PAYMENT ------------------------ #
def get_cart_total(user):
    cart_items = Cart.objects.filter(user=user).annotate(item_total=F("quantity") * F("product__price"))
    total_amount = cart_items.aggregate(Sum("item_total"))["item_total__sum"] or 0
    return total_amount
# -----------------------------------------------------------------------------------------------------------------
@login_required
def place_order_with_wallet(request):
    if request.method == "POST":
        user = request.user
        data = json.loads(request.body)

        address_id = data.get("address_id")
        payment_method = data.get("payment_method")

        if not address_id:
            return JsonResponse({"success": False, "message": "Address is required!"})

        if payment_method != "wallet":
            return JsonResponse({"success": False, "message": "Invalid payment method!"})

        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return JsonResponse({"success": False, "message": "Wallet not found!"})

        total_amount = get_cart_total(user)

        if total_amount <= 0:
            return JsonResponse({"success": False, "message": "Cart is empty!"})

        if wallet.balance < total_amount:
            return JsonResponse({"success": False, "message": "Insufficient wallet balance!"})

        try:
            with transaction.atomic():
                wallet.balance -= total_amount
                wallet.save()

                order = Order.objects.create(
                    user=user,
                    address_id=address_id,
                    total_amount=total_amount,
                    payment_method="wallet",
                    status="Paid"
                )

                Cart.objects.filter(user=user).delete()

            return JsonResponse({"success": True, "redirect_url": "/order-success/"})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"Order failed: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request method"})
# -----------------------------------------------------------------------------------------------------------------
@login_required
def apply_coupon(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            coupon_id = data.get("coupon_id")
            print(coupon_id)

            if not coupon_id:
                return JsonResponse({"success": False, "message": "No coupon selected."}, status=400)

            coupon = get_object_or_404(Coupon, id=coupon_id, is_deleted=False)

            if coupon.usage_limit <= 0:
                return JsonResponse({"success": False, "message": "Coupon usage limit reached."}, status=400)

            cart = get_object_or_404(Cart, user=request.user)
            cart_items = CartItem.objects.filter(cart=cart)

            if not cart_items.exists():
                return JsonResponse({"success": False, "message": "Your cart is empty!"}, status=400)

            cart_total = sum(item.quantity * item.product.offer_price for item in cart_items)
            shipping_cost = getattr(settings, "SHIPPING_COST", 30)
            total_amount = cart_total + shipping_cost  

            local_tz = pytz.timezone(settings.TIME_ZONE)
            current_time = now().astimezone(local_tz)
            start_date = coupon.start_date.astimezone(local_tz)
            end_date = coupon.end_date.astimezone(local_tz)

            if current_time < start_date:
                return JsonResponse({"success": False, "message": "This coupon is not active yet."}, status=400)
            if current_time > end_date:
                return JsonResponse({"success": False, "message": "This coupon has expired."}, status=400)

            if total_amount < coupon.min_order_amount:
                missing_amount = coupon.min_order_amount - total_amount
                return JsonResponse({
                    "success": False, 
                    "message": f"Minimum order amount for this coupon is ₹{coupon.min_order_amount}. Add ₹{missing_amount:.2f} more to apply."
                }, status=400)

            discount_amount = min(coupon.discount_amount, total_amount)
            total_amount -= discount_amount

            coupon.usage_limit -= 1
            coupon.save(update_fields=["usage_limit"])

            request.session["applied_coupon_code"] = coupon.code
            request.session["discount_amount"] = float(discount_amount)
            request.session.modified = True

            return JsonResponse({
                "success": True,
                "discount_amount": discount_amount,
                "total_amount": total_amount,
                "remaining_usage": coupon.usage_limit
            })

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid request format."}, status=400)
        except Coupon.DoesNotExist:
            return JsonResponse({"success": False, "message": "Coupon not found."}, status=400)
        except Exception as e:  
            return JsonResponse({"success": False, "message": "Something went wrong. Please try again."}, status=500)

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)








