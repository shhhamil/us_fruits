from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import update_session_auth_hash
from user_profile.models import Complaint
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from reportlab.lib import colors
import razorpay
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
    print(orders_data)  

    return render(request, 'user_profile/order_history.html', {
        'orders': orders_data,
        'subtotal': subtotal,
        'total_amount': total_amount  
    })


# --------------------------------------------------------------------------------------
@login_required
def cancel_order(request, order_id):
    print(f'order {order_id}')
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status != 'pending':
            return JsonResponse({'status': 'error', 'message': 'Only pending orders can be cancelled'}, status=400)

        with transaction.atomic():
            for item in order.items.all():
                item.product.stock += item.quantity
                item.product.save()

            if order.payment_method == "wallet":
                user_wallet, _ = Wallet.objects.get_or_create(user=request.user)
                user_wallet.balance += order.total
                user_wallet.save()

                transaction_record = WalletTransaction.objects.create(
                    wallet=user_wallet,
                    transaction_type="credit",
                    amount=order.total
                )

            order.status = Order.STATUS_CANCELLED
            order.cancellation_reason = data.get('reason', 'No reason provided')
            order.cancelled_at = timezone.now()
            order.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Order cancelled successfully, amount refunded to wallet' if order.payment_method == "wallet" else 'Order cancelled successfully'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
# -------------------------------------------------------------------------------------------------    
@csrf_exempt
def cancel_order_item(request, item_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            reason = data.get("reason")

            if not reason:
                return JsonResponse({"success": False, "error": "No reason provided"}, status=400)

            order_item = OrderItem.objects.get(id=item_id)

            if order_item.status != "pending":
                return JsonResponse({"success": False, "error": "Order cannot be cancelled"}, status=400)

            user = order_item.order.user
            wallet, _ = Wallet.objects.get_or_create(user=user)

            total_refund = order_item.price * order_item.quantity
            wallet.deposit(total_refund)

            order_item.product.stock += order_item.quantity
            order_item.product.save()

            order_item.status = "cancelled"
            order_item.cancel_reason = reason
            order_item.save()

            order = order_item.order
            remaining_items = order.orderitem_set.filter(status="pending")

            if not remaining_items.exists():
                if hasattr(order, "shipping_cost"):
                    shipping_cost = order.shipping_cost
                    wallet.deposit(shipping_cost)
                    total_refund += shipping_cost

                order.status = "cancelled"
                order.save()

            return JsonResponse({"success": True, "message": f"Order cancelled. ₹{total_refund} credited to wallet, stock updated."})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


# -------------------------------------------------------------------------------------
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'user_profile/view_order.html', {'order': order})

# ------------------------------------------------------------------------------------
@login_required
def wallet(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:10]
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
            "payment_capture": "1",
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
#---------------this for set a  Proper PDF Filename----------------------
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
#-----------Create PDF Document-----------
    pdf = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
#---------------Invoice Title (Shop Name and Address)-------------
    elements.append(Paragraph("<b>US Fruits </b>", styles["Title"]))   
    elements.append(Spacer(1, 10))  
# ------------------Bill Header--------------
    elements.append(Paragraph(f"<b>INVOICE - ORDER {order.id}</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
#---------------User Details Table---------------------------
    user_info = [
        ["User Name:", order.user.username],
        ["Order Date:", order.date_of_order.strftime('%d-%m-%Y')],
        ["Total Amount :", f" {order.total:.2f}"],
        ["Shipping Fee:", f" {shipping_cost:.2f}"],  
        ["Final Total:", f" {final_total:.2f}"],  
        ["Payment Status:", order.payment_status.capitalize()],
    ]
    table_user = Table(user_info, colWidths=[180, 220])
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
            f" {item.price:.2f}",
            f" {item.quantity * item.price:.2f}"
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
    elements.append(Spacer(1, 1))
    final_total_data = [
        ["Subtotal:", f" {order.total:.2f}"],
        ["Shipping Fee:", f" {shipping_cost:.2f}"],
        ["Grand Total:", f" {final_total:.2f}"],  
    ]
    table_total = Table(final_total_data, colWidths=[250, 100])
    table_total.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table_total)

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b> Thank you for shopping with us!!!</b>", styles["Heading3"]))
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

