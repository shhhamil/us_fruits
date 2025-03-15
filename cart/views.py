import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.contrib import messages
from django.views.decorators.http import require_POST
from user_profile.models import Address ,Wallet,WalletTransaction
from auth_admin.models import Product
import razorpay
from decimal import Decimal
from django.conf import settings
from cart.models import CartItem
from django.views.decorators.csrf import csrf_exempt  
from .models import Cart
import json
from auth_admin.models import OrderItem
from auth_admin.models import Order,OrderItem
from django.db.models import Sum, F, ExpressionWrapper, DecimalField

# ---------------------------------------------------------------
logger = logging.getLogger(__name__)
@login_required
def cart(request):
    if not request.user.is_authenticated:
        return redirect('Main_Login')
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('product').order_by('product__name')
    total_price = cart_items.aggregate(
        total=Sum(
            ExpressionWrapper(
                F('quantity') * F('product__offer_price'),
                output_field=DecimalField())))['total'] or 0 
    context = {
        'cart_items': cart_items,
        'total_price': total_price
    }
    return render(request, 'cart/cart.html', context)
# ----------------------------------------------------------------------------------------@-
@login_required
@require_POST
def add_to_cart(request, product_id):
    try:
        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(user=request.user)

            # Get quantity from request
            try:
                quantity = int(request.POST.get('quantity', 1))
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid quantity'}, status=400)

            # Check if product exists
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)

            # Quantity validation
            if quantity <= 0:
                return JsonResponse({'status': 'error', 'message': 'Quantity must be greater than 0'}, status=400)

            if quantity > product.stock:
                return JsonResponse({'status': 'error', 'message': f'Only {product.stock} items available in stock'}, status=400)

            # Get the cart item if it exists, else create it
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

            # ✅ Add new quantity instead of replacing it
            new_quantity = cart_item.quantity + quantity

            # ✅ Ensure the total does not exceed 5
            total_items_in_cart = sum(item.quantity for item in cart.cart_items.all())
            if total_items_in_cart + quantity > 5:
                return JsonResponse({'status': 'error', 'message': 'You can only order up to 5 products at a time.'}, status=400)

            cart_item.quantity = new_quantity
            cart_item.save()

            cart_count = sum(item.quantity for item in cart.cart_items.all())

            return JsonResponse({'status': 'success', 'message': 'Product added to cart successfully!', 'cart_count': cart_count})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An error occurred while adding to cart'}, status=500)

# -------------------------------------------------------------------------------------
@require_POST
@login_required
def update_cart(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')

        # Refresh the cart_item from the database to get the latest quantity
        cart_item.refresh_from_db()

        if action == 'increase':
            if cart_item.quantity >= cart_item.product.stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Sorry, only {cart_item.product.stock} items available in stock'
                }, status=400)

            # Check maximum limit AFTER refreshing
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
        
        # Calculate cart total
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

# 0--------------------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------------------
import logging
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

        # Log the incoming data
        logger.debug(f"Received data: {street}, {city}, {state}, {pin_code}, {country}, {phone}, {is_default}")

        # Validate fields
        if not all([street, city, state, pin_code, country, phone]):
            return JsonResponse({"success": False, "message": "Please fill all fields."})

        if len(phone) != 10:
            return JsonResponse({"success": False, "message": "Please enter a valid 10-digit phone number."})

        try:
            with transaction.atomic():
                # Create address
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

                # Set other addresses to non-default if a new default is selected
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
    """Redirects the user to the checkout page only if the cart is not empty."""
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
        shipping_cost = 30  
        total_amount = cart_total + shipping_cost

    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty. Please add items to proceed.")
        return redirect("cart")

    addresses = Address.objects.filter(user=request.user)
    wallet = Wallet.objects.filter(user=request.user).first()
    wallet_balance = wallet.balance if wallet else 0  

    if request.method == "POST":
        selected_address_id = request.POST.get("address")
        address = get_object_or_404(Address, id=selected_address_id, user=request.user)

        for cart_item in cart_items:
            if cart_item.product.stock < cart_item.quantity:
                messages.error(request, f"Not enough stock available for {cart_item.product.name}.")
                return redirect("Cart")

        with transaction.atomic():
            # Create the order
            order = Order.objects.create(
                user=request.user,
                address=address,
                total=total_amount,
                shipping_cost=shipping_cost,   
                payment_status="unpaid",
            )

            # Create order items and update stock
            for cart_item in cart_items:
                product = cart_item.product

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=cart_item.quantity,
                    price=product.offer_price
                )

                product.stock -= cart_item.quantity
                product.save()

            # Clear the cart
            cart_items.delete()

        messages.success(request, "Order placed successfully!")
        return redirect("order_history")

    context = {
        "cart_items": cart_items,
        "cart_total": cart_total,
        "shipping_cost": shipping_cost,
        "total_amount": total_amount,
        "addresses": addresses,
        "wallet_balance": wallet_balance,  
    }
    return render(request, "cart/checkout.html", context)

# -------------------------------- PLACE ORDER VIEW -------------------------------- #
@login_required
def place_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')
        payment_method = data.get('payment_method')
        razorpay_payment_id = data.get("razorpay_payment_id")

        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Your cart is empty.'})

        cart_items = CartItem.objects.filter(cart=cart)
        if not cart_items.exists():
            return JsonResponse({'success': False, 'message': 'Your cart is empty.'})

        total_amount = sum(item.quantity * item.product.offer_price for item in cart_items)
        
        # ✅ Set global shipping cost
        shipping_cost = settings.SHIPPING_COST if hasattr(settings, 'SHIPPING_COST') else 30
        total_amount += shipping_cost

        # COD restriction for orders above 1000
        if payment_method == "cod" and total_amount >= 1000:
            return JsonResponse({'success': False, 'message': 'COD is not available for orders above 1000.'})

        # Razorpay requires a payment ID
        if payment_method == "razorpay" and not razorpay_payment_id:
            return JsonResponse({'success': False, 'message': 'Use the "Pay with Razorpay" button instead.'})

        # Wallet balance check
        if payment_method == "wallet":
            user_wallet = Wallet.objects.get(user=request.user)
            if user_wallet.balance < total_amount:
                return JsonResponse({'success': False, 'message': 'Insufficient wallet balance.'})

        payment_status = 'paid' if payment_method in ['razorpay', 'wallet'] else 'unpaid'

        # ✅ **Check stock availability before creating an order**
        for item in cart_items:
            if item.product.stock < item.quantity:
                return JsonResponse({'success': False, 'message': f'Not enough stock for {item.product.name}.'})

        with transaction.atomic():
            # Create the order
            order = Order.objects.create(
                user=request.user,
                address=Address.objects.get(id=address_id),
                total=total_amount,
                shipping_cost=shipping_cost,
                payment_status=payment_status,
                payment_method=payment_method,
            )

            if payment_method == "razorpay":
                order.razorpay_payment_id = razorpay_payment_id

            # Deduct from wallet balance if paying via wallet
            if payment_method == "wallet":
                user_wallet.balance -= total_amount
                user_wallet.save()

            # Create Order Items and update stock
            for item in cart_items:
                product = item.product
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=item.product.offer_price
                )
                product.stock -= item.quantity
                product.save()

            # Clear the cart
            cart_items.delete()
            order.save()

        return JsonResponse({'success': True, 'redirect_url': '/order-history/'})

    except Exception as e:
        import traceback
        traceback.print_exc()  # Print full error details in the console
        return JsonResponse({'success': False, 'message': f'Failed to process order: {str(e)}'})
# ---------------------------- RAZORPAY ORDER CREATION ---------------------------- #
@csrf_exempt
def create_order(request):
    """Creates a Razorpay order and returns the order ID."""
    if request.method == "POST":
        try:
            amount_str = request.POST.get("amount")
            if not amount_str:
                return JsonResponse({"error": "Amount is required"}, status=400)

            try:
                amount = int(Decimal(amount_str) * 100)  # Convert to paise
            except ValueError:
                return JsonResponse({"error": "Invalid amount format"}, status=400)
            client = razorpay.Client(auth=(settings.R_ID, settings.R_SECRET))
            
            order_data = {
                "amount": amount,
                "currency": "INR",
                "payment_capture": 1
            }
            order = client.order.create(order_data)

            logger.info("Razorpay order created: %s", order)
            return JsonResponse(order)

        except Exception as e:
            logger.error("Error in Razorpay order creation: %s", str(e))
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


# ------------------------ PLACE ORDER WITH WALLET PAYMENT ------------------------ #
def get_cart_total(user):
    cart_items = Cart.objects.filter(user=user).annotate(item_total=F("quantity") * F("product__price"))
    total_amount = cart_items.aggregate(Sum("item_total"))["item_total__sum"] or 0
    return total_amount

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

        # Get user's wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return JsonResponse({"success": False, "message": "Wallet not found!"})

        # Fetch the total cart amount
        total_amount = get_cart_total(user)

        if total_amount <= 0:
            return JsonResponse({"success": False, "message": "Cart is empty!"})

        if wallet.balance < total_amount:
            return JsonResponse({"success": False, "message": "Insufficient wallet balance!"})

        # Atomic transaction to ensure data consistency
        try:
            with transaction.atomic():
                # Deduct wallet balance
                wallet.balance -= total_amount
                wallet.save()

                # Create order
                order = Order.objects.create(
                    user=user,
                    address_id=address_id,
                    total_amount=total_amount,
                    payment_method="wallet",
                    status="Paid"
                )

                # Clear the cart after order is placed
                Cart.objects.filter(user=user).delete()

            return JsonResponse({"success": True, "redirect_url": "/order-success/"})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"Order failed: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request method"})