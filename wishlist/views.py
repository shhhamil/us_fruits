from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Wishlist, Product
# ------------------------------
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, "wishlist/wishlist.html", {"wishlist_items": wishlist_items})
# --------------------------------------------
@login_required
def toggle_wishlist(request):
    if request.method == "POST":
        product = get_object_or_404(Product, id=request.POST.get("product_id"))
        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

        if created:
            return JsonResponse({"status": "success", "in_wishlist": True, "message": "Added to wishlist"})
        else:
            wishlist_item.delete()
            return JsonResponse({"status": "success", "in_wishlist": False, "message": "Removed from wishlist"})

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)
# ----------------------------------------------------
@login_required
def remove_from_wishlist(request, item_id):
    if request.method == "POST":
        wishlist_item = get_object_or_404(Wishlist, id=item_id, user=request.user)
        wishlist_item.delete()
        return JsonResponse({"status": "success", "message": "Item removed from wishlist"})

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
# ========================================
@login_required
def check_wishlist(request, product_id):
    in_wishlist = Wishlist.objects.filter(user=request.user, product_id=product_id).exists()
    return JsonResponse({"status": "success", "in_wishlist": in_wishlist})
