from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import update_session_auth_hash
from user_profile.models import Complaint
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from reportlab.lib import colors
import razorpay
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph , Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.contrib import messages
from .models import Address
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from auth_admin.models import Order, OrderItem
from django.http import JsonResponse
from auth_admin.models import Order
import json
from .models import Wallet,WalletTransaction
# Create your views here
# _____________________________________________________________________
@never_cache
@login_required
def profile(request):
    user = request.user  

    if request.method == "POST":
        new_name = request.POST.get("username")  
        if new_name:
            user.username = new_name   
            user.save()   
            return redirect("Profile")  
    return render(request, "user_profile/profile.html", {"user": user})
# ----------------------------------------------------------------------------------
@login_required
def change_password(request):
    
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        user = request.user 
#--------------- Validate current password---------------------------
        if not user.check_password(current_password):
            return render(request, "user_profile/password.html", {"error": "Current password is incorrect"})
#--------------- Check if new password matches confirm password--------------------
        if new_password != confirm_password:
            return render(request, "user_profile/password.html", {"error": "New passwords do not match"})
        user.set_password(new_password)
        user.save()
#--------------- Keep the user logged in after password change-------------------------
        update_session_auth_hash(request, user)
        return render(request, "user_profile/password.html", {"success": "Password changed successfully"})
    return render(request, "user_profile/password.html")
# ________________________________________________________________________________________________________________________
# ------------------ LIST ADDRESSES VIEW ------------------
@login_required
def list_address(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, "user_profile/add_address.html", {"addresses": addresses})
# ---------------------------------------------------------------
@login_required
def add_address(request):
    if request.method == "POST":
        user = request.user  
        if not user.is_authenticated:
            return JsonResponse({"success": False, "error": "User not logged in"}, status=400)

        street = request.POST.get("street")
        city = request.POST.get("city")
        state = request.POST.get("state")
        pin_code = request.POST.get("pin_code")
        phone = request.POST.get("phone")
        country = request.POST.get("country")
        is_default = request.POST.get("is_default") == "on"  

        address = Address.objects.create(
            user=user,  
            street=street,
            city=city,
            state=state,
            pin_code=pin_code,
            phone=phone,
            country=country,
            is_default=is_default,
        )

        return JsonResponse({"success": True, "id": address.id, "street": address.street, "city": address.city, "state": address.state, "pincode": address.pin_code, "phone": address.phone, "country": address.country, "is_default": address.is_default})

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)
# -------------------------------------------------------------------
@login_required
def edit_address(request, address_id):
    user = request.user

    try:
        address = Address.objects.get(id=address_id, user=user)
    except Address.DoesNotExist:
        return JsonResponse({"success": False, "error": "Address not found"}, status=404)


    if Order.objects.filter(address=address, status__in=["pending", "shipped"]).exists():
        return JsonResponse({
            "success": False,
            "error": "You cannot edit this address while an order is pending or shipped."
        }, status=400)

    if request.method == "POST":
        address.street = request.POST.get("street")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pin_code = request.POST.get("pin_code")
        address.phone = request.POST.get("phone")
        address.country = request.POST.get("country")
        address.is_default = request.POST.get("is_default") == "on"
        address.save()
        return JsonResponse({"success": True, "id": address.id})

    elif request.method == "GET":
        return JsonResponse({
            "success": True,
            "id": address.id,
            "street": address.street,
            "city": address.city,
            "state": address.state,
            "pin_code": address.pin_code,
            "phone": address.phone,
            "country": address.country,
            "is_default": address.is_default,
        })

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

# ------------------------------------------------------------------------------------------------------
@login_required
def delete_address(request, address_id):
    if request.method == "POST":
        user = request.user
        try:
            address = Address.objects.get(id=address_id, user=user)
            if Order.objects.filter(address=address, status__in=['pending', 'shipped']).exists():
                return JsonResponse({"success": False, "message": "You cannot delete this address while an order is pending or shipped."}, status=400)

            address.delete()
            return JsonResponse({"success": True, "message": "Address deleted successfully."})

        except Address.DoesNotExist:
            return JsonResponse({"success": False, "message": "Address not found."}, status=404)

    return JsonResponse({"success": False, "message": "Invalid request."}, status=400)
# ---------------------------------------------------------------
@login_required
def set_default_address(request, address_id):
    if request.method == "POST":
        user = request.user
        try:
            address = Address.objects.get(id=address_id, user=user)  
            Address.objects.filter(user=user).update(is_default=False)  
            address.is_default = True
            address.save()
            return JsonResponse({"success": True})
        except Address.DoesNotExist:
            return JsonResponse({"success": False, "error": "Address not found"}, status=404)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)
# --------------------------------------------------------------------------------------------------------------
@login_required
def order_history(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .order_by('-id')
        .select_related('user')
        .prefetch_related('items__product', 'complaints')   
    )

    subtotal = 0  
    orders_data = []  
    shipping_cost = 30  

    for order in orders:
        order_total = order.total - (order.discount_amount or 0)   
        subtotal += order_total  


        complaint = order.complaints.first() if hasattr(order, 'complaints') else None  

        orders_data.append({
            'id': order.id,
            'date_of_order': order.date_of_order.strftime("%b %d, %Y"),
            'status': order.status,
            'payment_status': order.payment_status,
            'payment_method': order.payment_method,
            'total_price': order_total,  
            'items': order.items.all(),
            'discount': order.discount_amount or 0,  
            'shipping_cost': shipping_cost,
            'final_total': order_total + shipping_cost,
            'complaint_status': complaint.status_complaint if complaint else None,  
            'complaint_id': complaint.id if complaint else None  
        })

    total_amount = subtotal + (shipping_cost * len(orders))  
    

    return render(request, 'user_profile/order_history.html', {
        'orders': orders_data,
        'subtotal': subtotal,
        'total_amount': total_amount  
    })

# --------------------------------------------------------------------------------------
def cancel_order(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id, user=request.user, status=Order.STATUS_PENDING)
            refund_total = 0

            for item in order.items.all():
                if item.status != 'cancelled':
                    refund_total += item.get_refund_amount()
                    item.product.stock += item.quantity
                    item.product.save()
                    item.status = 'cancelled'
                    item.save()

            refund_total += order.shipping_cost

            user_wallet = Wallet.objects.get(user=request.user)
            user_wallet.deposit(refund_total)

            order.status = Order.STATUS_CANCELLED
            order.cancelled_at = now()
            order.save()

            messages.success(request, f"Order cancelled. ₹{refund_total} refunded to your wallet.")
            return redirect('Order-history')

        except Order.DoesNotExist:
            messages.error(request, "Order not found or already processed.")
            return redirect('Error')

    return HttpResponseForbidden("Invalid request method")

# ---------------------------------------------------------------------------------------
def cancel_order_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if item.status == 'pending':
        refund_amount = item.get_refund_amount()
        item.status = 'cancelled'
        item.product.stock += item.quantity
        item.product.save()
        item.save()

        order = item.order
        if all(i.status == 'cancelled' for i in order.items.all()):
            refund_amount += order.shipping_cost
            order.status = 'cancelled'
            order.cancelled_at = now()
            order.save()

        user_wallet = Wallet.objects.get(user=request.user)
        user_wallet.deposit(refund_amount)

        messages.success(request, f"Order item cancelled. ₹{refund_amount} refunded to your wallet.")
    else:
        messages.error(request, 'This order item cannot be cancelled.')

    return redirect('order_detail', order_id=item.order.id)


# -------------------------------------------------------------------------------------
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'user_profile/view_order.html', {'order': order})

# ------------------------------------------------------------------------------------
@login_required
def wallet(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:5]
    return render(request, "user_profile/wallet.html", {
        "wallet": wallet,
        "transactions": transactions
    })

# ---------------------------------------------------------------------------------------
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
def add_money(request, amount):
    try:
        if amount <= 0:
            return JsonResponse({"error": "Invalid amount"}, status=400)

        data = {
            "amount": amount * 100,
            "currency": "INR",
            "payment_capture": 1,
        }

        order = razorpay_client.order.create(data)

        return JsonResponse({
            "key": settings.RAZORPAY_KEY_ID,
            "amount": amount * 100,
            "currency": "INR",
            "order_id": order["id"],
        })
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
# -------------------------------------------------------------------------------
@csrf_exempt
@login_required
def payment_success(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user = request.user
            wallet, created = Wallet.objects.get_or_create(user=user)

            razorpay_payment_id = data.get("razorpay_payment_id")
            amount = data.get("amount")

            if not amount:
                return JsonResponse({"error": "Amount is missing"}, status=400)

            amount = Decimal(amount) / 100  

            try:
                razorpay_client.payment.fetch(razorpay_payment_id)  
                wallet.balance += amount
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type="credit"
                )

                return JsonResponse({"message": "Wallet updated successfully", "new_balance": str(wallet.balance)})
            except Exception:
                return JsonResponse({"error": "Payment verification failed"}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)
# --------------------------------------------------------------------
def generate_invoice(request, order_id):
    order = Order.objects.get(id=order_id)
    shipping_cost = 30
    final_total = order.total + shipping_cost

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

    pdf = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>US Fruits</b>", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>INVOICE - ORDER #{order.id}</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    address = order.address

    user_info = [
        ["User Name:", order.user.username],
        ["Order Date:", order.date_of_order.strftime('%d-%m-%Y')],
        ["Phone:", getattr(address, 'phone', 'N/A')],
        ["Shipping Address:", f"{getattr(address, 'street', '')}, {getattr(address, 'city', '')}, "
                              f"{getattr(address, 'state', '')} - {getattr(address, 'pin_code', '')}, "
                              f"{getattr(address, 'country', '')}"],
        ["Total Amount:", f"Rs {order.total:.2f}"],
        ["Shipping Fee:", f"Rs {shipping_cost:.2f}"],
        ["Grand Total:", f"Rs {final_total:.2f}"],
        ["Payment Status:", order.payment_status.capitalize()],
    ]

    table_user = Table(user_info, colWidths=[180, 300])
    table_user.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(table_user)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>Items Purchased</b>", styles["Heading2"]))
    elements.append(Spacer(1, 5))

    item_data = [["Product Name", "Qty", "Price", "Total"]]
    for item in OrderItem.objects.filter(order=order):
        item_data.append([
            item.product.name,
            item.quantity,
            f"Rs {item.price:.2f}",
            f"Rs {item.quantity * item.price:.2f}"
        ])

    table_items = Table(item_data, colWidths=[200, 60, 100, 100])
    table_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#82ae46")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table_items)
    elements.append(Spacer(1, 15))

    final_total_data = [
        ["Shipping Fee:", f"Rs {shipping_cost:.2f}"],
        ["Grand Total:", f"Rs {final_total:.2f}"],
    ]
    table_total = Table(final_total_data, colWidths=[360, 100])
    table_total.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table_total)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Thank you for shopping with us!</b>", styles["Heading3"]))

    pdf.build(elements)
    return response
# ------------------------------------------------------
@login_required
def submit_complaint(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if item.complaints.exists():
        messages.warning(request, "You have already submitted a complaint for this item.")
        return redirect('order_detail', order_id=order.id)

    if request.method == "POST":
        image = request.FILES.get('image')
        description = request.POST.get('description')

        if not image or not description:
            messages.error(request, "Image and description are required!")
            return redirect('submit_complaint', order_id=order.id, item_id=item.id)

        complaint = Complaint.objects.create(
            order=order,
            item=item,
            image=image,
            description=description,
            status_complaint='pending'
        )
        messages.success(request, "Complaint submitted successfully. It is now pending review.")
        return redirect('order_detail', order_id=order.id)

    return render(request, "user_profile/complaint.html", {"order": order, "item": item})

# ------------------------------------------------------
@csrf_exempt
@login_required
def complete_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            razorpay_payment_id = data.get("razorpay_payment_id")
            order_id = data.get("order_id")

            if not razorpay_payment_id or not order_id:
                return JsonResponse({'success': False, 'message': 'Missing payment ID or order ID'})

            order = get_object_or_404(Order, id=order_id, user=request.user)

            if order.payment_method != "razorpay":
                return JsonResponse({'success': False, 'message': 'Invalid payment method for this order.'})

            if order.payment_status == "paid":
                return JsonResponse({'success': False, 'message': 'Order already paid.'})

            order.payment_status = "paid"
            order.razorpay_payment_id = razorpay_payment_id
            order.save()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})
