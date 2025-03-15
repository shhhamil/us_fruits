from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Category, Product,OrderItem
from .models import CustomUser
from django.contrib import messages
from .models import Order
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from django.db.models import Q
from django.views.decorators.http import require_POST
import json
from django.db.models import Sum
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill  
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
# ______________________________________________________________________________________________________________
# ---------------------------------------LOGIN VIEWS------------------------------------------------------------
def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return redirect('Admin_Login')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_superuser:
                if not user.is_active:
                    messages.error(request, "You're blocked. Please contact support.")
                    return redirect('Admin_Login')
                login(request, user)
                return redirect('Admin_Dashbord')
            else:
                messages.error(request, 'You do not have permission to access the admin panel.')
        else:
            messages.error(request, 'Invalid user credentials')
        return redirect('Admin_Login')
    return render(request, 'auth_admin/Admin_login.html')
# ______________________________________________________________________________________________________________
# ------------------------------------DASHBORD VIEWWS-----------------------------------------------------------
@never_cache
def admin_dashbord(request):
    if not request.user.is_superuser:
        messages.error(request, 'You are not authorized to access this page.')
        return redirect('Admin_Login')
    return render(request, 'auth_admin/admin_dashbord.html')
# ______________________________________________________________________________________________________________
# ---------------------------------------LOGOUT VIEWS-----------------------------------------------------------
@never_cache
def admin_logout(request):
    logout(request)   
    return redirect('Admin_Login')
# ______________________________________________________________________________________________________________
# -----------------------------------------View for category management page------------------------------------
def Category_Manegement(request):
    page = request.GET.get('page', 1)   
    search = request.GET.get('search', '')   
    categories = Category.objects.all()
    
    if search:
        categories = categories.filter(name__icontains=search)
    
    paginator = Paginator(categories, 10)  
    try:
        categories_page = paginator.page(page)
    except PageNotAnInteger:
        categories_page = paginator.page(1)  
    except EmptyPage:
        categories_page = paginator.page(paginator.num_pages)   
    
    context = {'categories': categories_page, 'total_categories': categories.count(), 'search_term': search}
    return render(request, 'auth_admin/category.html', context)
# _______________________________________________________________________________________________________________
#==================================== Add Category===============================================================
def add_category(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        discount = request.POST.get('discount', '').strip()  


        if not name:
            messages.error(request, "Category name is required!")
            return redirect('Add_Category')

        if not description:
            messages.error(request, "Description is required!")
            return redirect('Add_Category')

        if discount:
            try:
                discount = float(discount)
                if discount < 0 or discount > 100:
                    messages.error(request, "Discount must be between 0 and 100!")
                    return redirect('Add_Category')
            except ValueError:
                messages.error(request, "Invalid discount value!")
                return redirect('Add_Category')
        else:
            discount = 0   

        if Category.objects.filter(name__iexact=name).exists():
            messages.error(request, "Category already exists!")
            return redirect('Add_Category')

        
        Category.objects.create(name=name, description=description, discount_percentage=discount)
        messages.success(request, "Category added successfully!")
        return redirect('Category')  

    categories = Category.objects.all()  
    return render(request, 'auth_admin/add_cate.html', {"categories": categories})

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        discount = request.POST.get('discount', '').strip() 

        if not name:
            messages.error(request, "Category name is required!")
            return redirect('Edit_Category', category_id=category.id)

        if not description:
            messages.error(request, "Description is required!")
            return redirect('Edit_Category', category_id=category.id)

        if discount:
            try:
                discount = float(discount)
                if discount < 0 or discount > 100:
                    messages.error(request, "Discount must be between 0 and 100!")
                    return redirect('Edit_Category', category_id=category.id)
            except ValueError:
                messages.error(request, "Invalid discount value!")
                return redirect('Edit_Category', category_id=category.id)
        else:
            discount = category.discount_percentage  

        
        if Category.objects.filter(name__iexact=name).exclude(id=category.id).exists():
            messages.error(request, "Category with this name already exists!")
            return redirect('Edit_Category', category_id=category.id)

       
        category.name = name
        category.description = description
        category.discount_percentage = discount  
        category.save()

        messages.success(request, "Category updated successfully!")
        return redirect('Category')  

    return render(request, 'auth_admin/edit_cate.html', {'category': category})
# ______________________________________________________________________________________________________________
# --------------------------------------Delete Category---------------------------------------------------------
def soft_delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if category.is_active:
        category.is_active = False
        messages.success(request, "Category disabled successfully!")
    else:
        category.is_active = True
        messages.success(request, "Category restored successfully!")

    category.save()
    return redirect('Category')

# _______________________________________________________________________________________________________________
# ----------------------------------------PRODUCT VIEWS----------------------------------------------------------
def Product_Management(request):
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '')
    
    products = Product.objects.filter(is_active=True).order_by('name')
    if search:
        products = products.filter(name__icontains=search)
    
    paginator = Paginator(products, 5)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    context = {
        'products': products_page,
        'total_products': products.count(),
        'search_term': search
    }
    return render(request, 'auth_admin/product.html', context)

# ==========================================================================++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# -------------------------------------View to add a new product----------------------------------------
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        offer_percentage = request.POST.get('offer_percentage', 0)
        stock = request.POST.get('stock')
        is_active = request.POST.get('is_active') == 'on'
        description = request.POST.get('description', '').strip()  
        photo_1 = request.FILES.get('photo_1')
        photo_2 = request.FILES.get('photo_2')
        photo_3 = request.FILES.get('photo_3')

        try:
            price = float(price)
            stock = int(stock)
            offer_percentage = float(offer_percentage)
        except ValueError:
            messages.error(request, "Invalid price, stock, or discount value!")
            return redirect('add_product')

        if not name:
            messages.error(request, "Product name is required!")
            return redirect('add_product')
        if not description:
            messages.error(request, "Description is required!")
            return redirect('add_product')
        if not category_id:
            messages.error(request, "Category is required!")
            return redirect('add_product')
        if price < 0:
            messages.error(request, "Price cannot be negative!")
            return redirect('add_product')
        if not (0 <= offer_percentage <= 100):
            messages.error(request, "Offer percentage must be between 0 and 100!")
            return redirect('add_product')
        if stock < 0:
            messages.error(request, "Stock cannot be negative!")
            return redirect('add_product')
        if not photo_1:
            messages.error(request, "At least one photo is required!")
            return redirect('add_product')

       
        category = get_object_or_404(Category, id=category_id)

        
        offer_price = round(price - (price * offer_percentage / 100), 2)

        try:
            Product.objects.create(
                name=name,
                category=category,
                price=price,
                offer_percentage=offer_percentage,
                offer_price=offer_price,
                stock=stock,
                is_active=is_active,
                description=description,   
                photo_1=photo_1,
                photo_2=photo_2,
                photo_3=photo_3
            )
            messages.success(request, "Product added successfully!")
            return redirect('Product')
        except Exception as e:
            messages.error(request, f"Error creating product: {str(e)}")
            return redirect('add_product')

    categories = Category.objects.all()
    return render(request, 'auth_admin/add_pro.html', {'categories': categories})
#_____________________________________________________________________________________________________________________________________
#------------------------------------------ View to edit an existing product----------------------------------------------------------
def edit_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        offer_percentage = request.POST.get('offer_percentage', 0)
        stock = request.POST.get('stock')
        is_active = request.POST.get('is_active') == 'on'
        description = request.POST.get('description', '').strip()  
        photo_1 = request.FILES.get('photo_1')
        photo_2 = request.FILES.get('photo_2')
        photo_3 = request.FILES.get('photo_3')
 
        try:
            price = float(price)
            stock = int(stock)
            offer_percentage = float(offer_percentage)
        except ValueError:
            messages.error(request, "Invalid price, stock, or discount value!")
            return redirect('Edit_Product', pk=pk)

 
        if not name:
            messages.error(request, "Product name is required!")
            return redirect('Edit_Product', pk=pk)
        if not description:
            messages.error(request, "Description is required!")
            return redirect('Edit_Product', pk=pk)
        if not category_id:
            messages.error(request, "Category is required!")
            return redirect('Edit_Product', pk=pk)
        if price < 0:
            messages.error(request, "Price cannot be negative!")
            return redirect('Edit_Product', pk=pk)
        if not (0 <= offer_percentage <= 100):
            messages.error(request, "Offer percentage must be between 0 and 100!")
            return redirect('Edit_Product', pk=pk)
        if stock < 0:
            messages.error(request, "Stock cannot be negative!")
            return redirect('Edit_Product', pk=pk)

 
        category = get_object_or_404(Category, id=category_id)

        try:
 
            product.name = name
            product.category = category
            product.price = price
            product.offer_percentage = offer_percentage
            product.stock = stock
            product.is_active = is_active
            product.description = description   
            product.offer_price = round(price - (price * offer_percentage / 100), 2)

 
            if photo_1:
                product.photo_1 = photo_1
            if photo_2:
                product.photo_2 = photo_2
            if photo_3:
                product.photo_3 = photo_3

            product.save()
            messages.success(request, "Product updated successfully!")
            return redirect('Product')
            
        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")
            return redirect('Edit_Product', pk=pk)
    
    return render(request, 'auth_admin/edit_pro.html', {'product': product, 'categories': categories})
# ________________________________________________________________________________________________________________________________
#------------------------------------------ View to see the details of a product---------------------------------------------------
def view_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    images = [img.url for img in [product.photo_1, product.photo_2, product.photo_3] if img]
    
  
    final_price = product.offer_price if product.offer_percentage > 0 else product.price

    return render(request, 'auth_admin/view_pro.html', {
        'product': product,
        'images': images,
        'final_price': final_price,  
    })
# ___________________________________________________________________________________________________________________________________-___
# -------------------------View to soft delete a product--------------------------------------------------------------------------------
def soft_delete_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    product.is_active = not product.is_active
    product.save()
    if product.is_active:
        messages.success(request, "Product restored successfully!")
    else:
        messages.success(request, "Product disabled successfully!")
    return redirect('Product')

# ______________________________________________________________________________________________________________________________
# -------------------------------------------------user--------------------------------------------------------------------------
login_required
def user_management(request):
    page = request.GET.get('page', 1)  
    search = request.GET.get('search', '').strip()

#------------ Search users by email or username and exclude soft-deleted users--------------------------------------
    users = CustomUser.objects.filter(
        Q(username__icontains=search) | Q(email__icontains=search),
        is_active=True  
    ).order_by('id')

    paginator = Paginator(users, 7)  
    try:
        users_page = paginator.page(page)
    except (PageNotAnInteger, ValueError):  
        users_page = paginator.page(1)   
    except EmptyPage:
        users_page = paginator.page(paginator.num_pages)  

    context = {
        'users': users_page,
        'total_users': users.count(),
        'search_term': search  
    }
    return render(request, 'auth_admin/user.html', context)

# __________________________________________________________________________________________________________________________
# -------------------------------------------Block User------------------------------------------------------------------------------
def block_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if user.is_superuser:
        messages.error(request, "You cannot block an admin user!")
        return redirect("User_Management")

    user.is_active = not user.is_active
    user.save()

    status = "unblocked" if user.is_active else "blocked"
    messages.success(request, f"User {user.username} has been {status}.")
    
    return redirect("User_Management")
# ---------------------------------------------------------------------------------------------------------------------------------
# _________________________________________Order vews______________________________________________________________________
def order_management(request):
    status_filter = request.GET.get('status', 'all').strip().lower()

    # ---------------------Filter orders based on status-----------------------------
    orders = Order.objects.all().order_by('-date_of_order')

    if status_filter in dict(Order.STATUS_CHOICES): 
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 5)
    page = request.GET.get('page', 1)

    try:
        orders_page = paginator.page(page)
    except (PageNotAnInteger, ValueError):
        orders_page = paginator.page(1) 
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages) 

    total_price = orders.aggregate(Sum('total'))['total__sum'] or 0

    context = {
        'orders': orders_page,
        'current_status': status_filter,
        'total_orders': orders.count(),
        'total_price': total_price,
    }
    return render(request, 'auth_admin/order.html', context)
# __________________________________________________________________________________________________________________________________
# ----------------------------------------------------------------------------------------------------------------------------------
@login_required
@require_POST
def update_order_status(request, orderId):
    try:            
        data = json.loads(request.body)
        new_status = data.get('status', '').strip().lower()

        order = get_object_or_404(Order, id=orderId)

        # Validate Order Status
        valid_statuses = ["pending", "shipped", "delivered", "cancelled"]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'message': 'Invalid order status!'}, status=400)

        # Update order status
        order.status = new_status

        # ✅ Automatically update payment status to 'paid' if delivered
        if new_status == "delivered":
            order.payment_status = "paid"

        order.save()

        return JsonResponse({'success': True, 'order_status': order.status, 'payment_status': order.payment_status})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data!'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
# # -----------------------------------------------------------------------------------
def get_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    total_amount = sum(item.product.offer_price * item.quantity for item in order.items.all()) + 30

    order_data = {
        "id": order.id,
        "created_at": order.date_of_order.strftime("%b %d, %Y"),
        "status": order.status,
        "payment_method": order.payment_status,
        "total_amount": total_amount,  
        "address": {
            "street": order.address.street if order.address else "N/A",
            "city": order.address.city if order.address else "N/A",
            "state": order.address.state if order.address else "N/A",
            "pin_code": order.address.pin_code if order.address else "N/A",
            "phone": order.address.phone if order.address else "N/A",
        },
        "items": [
            {
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": item.product.price * item.quantity, 
                "product_image": item.product.photo_1.url if item.product.photo_1 else "",
            }
            for item in order.items.all()
        ]
    }
    print(f"---------------------{order_data}")
    return JsonResponse(order_data)
# -----------------------------------------------------------------------------------------------------
@login_required
def sales_report(request):
    period = request.GET.get('period', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    page = request.GET.get('page', 1)
    today = timezone.now().date()
    
    if period == 'today':
        orders = Order.objects.filter(date_of_order__date=today)
    elif period == 'weekly':
        start_of_week = today - timedelta(days=today.weekday())
        orders = Order.objects.filter(date_of_order__date__gte=start_of_week)
    elif period == 'monthly':
        start_of_month = today.replace(day=1)
        orders = Order.objects.filter(date_of_order__date__gte=start_of_month)
    elif period == 'yearly':
        start_of_year = today.replace(month=1, day=1)
        orders = Order.objects.filter(date_of_order__date__gte=start_of_year)
    elif period == 'custom' and start_date and end_date:
        try:
            start_date_obj = parse_date(start_date)
            end_date_obj = parse_date(end_date)
            if end_date_obj < start_date_obj:
                return render(request, 'auth_admin/sales.html', {'error': 'End date must be after start date','period': period})
            orders = Order.objects.filter(date_of_order__date__range=[start_date_obj, end_date_obj])
        except (ValueError, TypeError):
            return render(request, 'auth_admin/sales.html', {'error': 'Invalid date format','period': period})
    else:
        orders = Order.objects.all()
    
    orders = orders.order_by('-date_of_order')
    
    total_sales = orders.aggregate(total=Sum('total'))['total'] or 0
    total_orders = orders.count()
    total_products_sold = OrderItem.objects.filter(order__in=orders).aggregate(total=Sum('quantity'))['total'] or 0


    
    completed_orders = orders.filter(status='delivered').count()
    cancelled_orders = orders.filter(status='cancelled').count()


    
    
    stats = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_products': total_products_sold,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
    }
    paginator = Paginator(orders, 10)
    try:
        paginated_orders = paginator.page(int(page))
    except (PageNotAnInteger, EmptyPage):
        paginated_orders = paginator.page(1)
    context = {
        'orders': paginated_orders,
        'stats': stats,
        'period': period,
        'message': request.GET.get('message')
    }
    
    return render(request, 'auth_admin/sales.html', context)
# ---------------------------------------------------------------------------------------------------------
@login_required
def export_sales_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{datetime.now().strftime("%Y%m%d")}.pdf"'
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=30, alignment=1, textColor=colors.HexColor('#82ae46'))
    elements.append(Paragraph("Sales Report", title_style))
    elements.append(Spacer(1, 20))
    orders = Order.objects.all().order_by('-date_of_order')
    table_data = [['Order ID', 'Date', 'Customer', 'Total Amount', 'Status', 'Payment']]
    for order in orders:
        row = [
            f'#{order.id}',
            order.date_of_order.strftime('%Y-%m-%d'),
            order.user.username if order.user else 'Guest',
            f'₹{order.total:,.2f}',
            order.status,
            order.payment_status
        ]
        table_data.append(row)
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#82ae46')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
# ------------------------------------------------------------------------------------
@login_required
def export_sales_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"
    headers = ['Order ID', 'Date', 'Customer', 'Total Amount', 'Status', 'Payment']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='82AE46', fill_type='solid')
    orders = Order.objects.all().order_by('-date_of_order')
    for row, order in enumerate(orders, 2):
        ws.cell(row=row, column=1, value=f'#{order.id}')
        ws.cell(row=row, column=2, value=order.date_of_order.strftime('%Y-%m-%d'))
        ws.cell(row=row, column=3, value=order.user.username if order.user else 'Guest')
        ws.cell(row=row, column=4, value=f'₹{order.total:.2f}')
        ws.cell(row=row, column=5, value=order.status)
        ws.cell(row=row, column=6, value=order.payment_status)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response
# ----------------------------------------------------------------------------------------------
@login_required
def filter_sales(request, period):
    today = datetime.today()
    if period == 'daily':
        start_date = today.replace(hour=0, minute=0, second=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'monthly':
        start_date = today.replace(day=1)
        end_date = today.replace(day=28) + timedelta(days=4)
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:
        return render(request, 'sales/dashboard.html', {'error': 'Invalid period'})
    orders = Order.objects.filter(date_of_order__range=[start_date, end_date])
    return render(request, 'auth_admin/sales.html', {'orders': orders})
# -------------------------------------------------------------------------
@login_required
def filter_custom_date(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        orders = Order.objects.filter(date_of_order__range=(start_date, end_date))
    else:
        orders = Order.objects.none()
    return render(request, 'auth_admin/sales.html', {'orders': orders})

