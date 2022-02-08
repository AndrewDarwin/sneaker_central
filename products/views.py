from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.functions import Lower

from .models import Product, Category, Review, WishList
from profiles.models import UserProfile
from .forms import ProductForm, ReviewForm

# Views

def all_products(request):
    """ A view to show all products, including sorting and search queries """

    products = Product.objects.all()
    query = None
    categories = None
    sort = None
    direction = None

    if request.GET:
        if 'sort' in request.GET:
            sortkey = request.GET['sort']
            sort = sortkey
            if sortkey == 'name':
                sortkey = 'lower_name'
                products = products.annotate(lower_name=Lower('name'))
            if sortkey == 'category':
                sortkey = 'category__name'
            if 'direction' in request.GET:
                direction = request.GET['direction']
                if direction == 'desc':
                    sortkey = f'-{sortkey}'
            products = products.order_by(sortkey)
            
        if 'category' in request.GET:
            categories = request.GET['category'].split(',')
            products = products.filter(category__name__in=categories)
            categories = Category.objects.filter(name__in=categories)

        if 'q' in request.GET:
            query = request.GET['q']
            if not query:
                messages.error(request, "You didn't enter any search criteria!")
                return redirect(reverse('products'))
            
            queries = Q(name__icontains=query) | Q(description__icontains=query)
            products = products.filter(queries)

    current_sorting = f'{sort}_{direction}'

    context = {
        'products': products,
        'search_term': query,
        'current_categories': categories,
        'current_sorting': current_sorting,
    }

    return render(request, 'products/products.html', context)


def product_detail(request, product_id):
    """ A view to show individual product details """

    product = get_object_or_404(Product, pk=product_id)
    review_form = None
    is_on_wishlist = False
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.get(user=request.user)
        review_form = ReviewForm(initial={'product': product, 'user_profile': user_profile})
        try:
            user_wishlist = WishList.objects.get(user_profile__user=request.user)
            is_on_wishlist = product in user_wishlist.product.all()
        except WishList.DoesNotExist as e:
            pass
    comments = Review.objects.filter(product=product)
    print(f'product is in wishlist {is_on_wishlist}')
    context = {
        'product': product,
        'comments': comments,
        'review_form': review_form,
        'is_on_wishlist': is_on_wishlist
    }

    return render(request, 'products/product_detail.html', context)


def product_add_comment(request, product_id):
    """ A view to show individual product details """
    print(f'Review posted {request.POST}')
    product = get_object_or_404(Product, pk=product_id)
    user_profile = UserProfile.objects.get(user=request.user)
    review_data = ReviewForm(request.POST)
    # if review_data.is_valid():
    #     review_data.save()
    new_comment = Review(product=product, review=request.POST.get('review'), user_profile=user_profile)
    new_comment.save()
    comments = Review.objects.filter(product=product)
    review_form = ReviewForm()
    context = {
        'product': product,
        'comments': comments,
        'review_form': review_form
    }

    return render(request, 'products/product_detail.html', context)



def product_add_to_wishlist(request, product_id):
    """ A view to show individual product details """
    product = get_object_or_404(Product, pk=product_id)
    user_profile = UserProfile.objects.get(user=request.user)
    user_wishlist, created = WishList.objects.get_or_create(user_profile=user_profile)
    user_wishlist.product.add(product)
    user_wishlist.save()
    return redirect(reverse('product_detail', kwargs={'product_id': product_id}))



@login_required
def add_product(request):
    """ Add a product to the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry, only store owners can do that.')
        return redirect(reverse('home'))

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Successfully added product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(request, 'Failed to add product. Please ensure the form is valid.')
    else:
        form = ProductForm()
        
    template = 'products/add_product.html'
    context = {
        'form': form,
    }

    return render(request, template, context)


@login_required
def edit_product(request, product_id):
    """ Edit a product in the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry, only store owners can do that.')
        return redirect(reverse('home'))

    product = get_object_or_404(Product, pk=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Successfully updated product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(request, 'Failed to update product. Please ensure the form is valid.')
    else:
        form = ProductForm(instance=product)
        messages.info(request, f'You are editing {product.name}')

    template = 'products/edit_product.html'
    context = {
        'form': form,
        'product': product,
    }

    return render(request, template, context)


@login_required
def delete_product(request, product_id):
    """ Delete a product from the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry, only store owners can do that.')
        return redirect(reverse('home'))

    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    messages.success(request, 'Product deleted!')
    return redirect(reverse('products'))