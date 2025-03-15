from django.shortcuts import render, redirect 
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph , Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.utils import timezone
from decimal import Decimal 
from .models import Address
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from auth_admin.models import Order, OrderItem
from django.contrib import messages
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
# ---------------------------------------------------------------------------------------
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

            # Prevent deletion if the address is linked to pending/shipped orders
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
def order_history(request):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-id')

        subtotal = 0
        for order in orders:
            order.total_price = sum(item.product.price * item.quantity for item in order.items.all())
            subtotal += order.total_price   

        shipping_cost = 30   
        total_amount = subtotal + shipping_cost

        return render(request, 'user_profile/order_history.html', {
            'orders': orders,
            'subtotal': subtotal,
            'total_amount': total_amount
        })
    else:
        return redirect('Main_Login')
# --------------------------------------------------------------------------------------
@login_required
def cancel_order(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order = Order.objects.get(id=order_id, user=request.user)

            if order.status != 'pending':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Only pending orders can be cancelled'
                }, status=400)

            with transaction.atomic():
                # Increase product stock for each item in the order
                for item in order.items.all():
                    item.product.stock += item.quantity
                    item.product.save()

                # Refund to wallet if paid by wallet
                if order.payment_status == "wallet":
                    user_wallet, created = Wallet.objects.get_or_create(user=request.user)
                    user_wallet.balance += order.total_amount
                    user_wallet.save()

                # Update order status
                order.status = Order.STATUS_CANCELLED
                order.cancellation_reason = data.get('reason', 'No reason provided')
                order.cancelled_at = timezone.now()
                order.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Order cancelled successfully, amount refunded to wallet' if order.payment_status == "wallet" else 'Order cancelled successfully'
            })

        except Order.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Order not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)
# ------------------------------------------------------------------------------------
@login_required
def wallet(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:11]  
    
    return render(request, "user_profile/wallet.html", {
        "wallet": wallet,
        "transactions": transactions
    })
# ------------------------------------------------
@login_required
def add_money(request):
    if request.method == "POST":
        user = request.user
        data = json.loads(request.body)
        amount = data.get("amount")

        if not amount or amount <= 0:
            return JsonResponse({"success": False, "message": "Invalid amount!"})

        wallet, created = Wallet.objects.get_or_create(user=user)
        wallet.balance += amount
        wallet.save()

        return JsonResponse({"success": True, "message": "Money added successfully!", "balance": wallet.balance})

    return JsonResponse({"success": False, "message": "Invalid request method"})
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