from django.shortcuts import render, get_object_or_404
from auth_admin.models import Category,Product
from django.core.paginator import Paginator
from django.shortcuts import render
from django.core.paginator import Paginator
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import F, Max ,DecimalField
from django.db.models.functions import Greatest
from django.core.paginator import Paginator
# ----------------------------------------------------------------------------------------------
def shop(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    
    products = Product.objects.filter(is_active=True).select_related('category').annotate(
        max_discount=Greatest(
            F('offer_percentage'), 
            F('category__discount_percentage'), 
            output_field=DecimalField()
        )
    )

    categories = Category.objects.filter(is_active=True)

    category = request.GET.get('category', 'all')
    sort_option = request.GET.get('sort', 'default')
    search_query = request.GET.get('search', '')

    try:
        min_price = float(request.GET.get('min_price', 0))
        max_price = float(request.GET.get('max_price', 10000))
    except (ValueError, TypeError):
        min_price, max_price = 0, 10000

    max_db_price = Product.objects.filter(is_active=True).aggregate(Max('offer_price'))['offer_price__max'] or 10000
    max_price = min(max_price, max_db_price)

    if category.isdigit():
        products = products.filter(category_id=int(category))

    products = products.filter(offer_price__gte=min_price, offer_price__lte=max_price)

    if search_query:
        products = products.filter(name__icontains=search_query)

    sorting_options = {
        'price_low': 'offer_price',
        'price_high': '-offer_price',
        'name_asc': 'name',
        'name_desc': '-name',
    }

    if sort_option in sorting_options:
        products = products.order_by(sorting_options[sort_option])
    else:
        products = products.order_by('-id')

    paginator = Paginator(products, 9)
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category,
        'sort_option': sort_option,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': search_query,
        'total_products': paginator.count
    }

    return render(request, 'shop/shop.html', context)

# ___________________________________________________________________________________________________________________________
def single_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product_id)[:4]

    product.max_discount = max(product.offer_percentage or 0, product.category.discount_percentage or 0)

    for p in related_products:
        p.max_discount = max(p.offer_percentage or 0, p.category.discount_percentage or 0)

    return render(request, 'shop/single_product.html', {
        'product': product,
        'related_products': related_products,
    })

# --------------------------------------------------------------------------------------------------------------
def check_authentication(request):
    return JsonResponse({'is_authenticated': request.user.is_authenticated})