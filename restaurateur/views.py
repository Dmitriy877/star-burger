from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
import operator

from geopy import distance

from foodcartapp.models import Product, Restaurant, Order
from locations.models import Location
from foodcartapp.models import RestaurantMenuItem


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):

    def get_distance_to_restaurant(restaurant_address, delivery_address, locations):
        restaurant_location = locations.get(address=restaurant_address)
        order_location = locations.get(address=delivery_address)
        return round(distance.distance((restaurant_location.lon, restaurant_location.lat), (order_location.lon, order_location.lat)).km, 2)

    def get_common_restaurants(restaurants):
        print('common_restaurants', restaurants)
        common_restaurants = restaurants[0]
        for s in restaurants[1:]:
            common_restaurants = common_restaurants.intersection(s)
        return list(common_restaurants)

    def get_sorted_by_distance_possibly_restaurants_to_cook(orders, restaurant_menu_items, locations):
        for order in orders:
            print('order', order)
            restaurants = []
            for product in order.order_items.all():
                possibly_restaurants = restaurant_menu_items.filter(product=product.product, availability=True)
                restaurants.append(set(restaurant.restaurant for restaurant in possibly_restaurants))
            common_restaurants = get_common_restaurants(restaurants)
            for restaurant in common_restaurants:
                restaurant.distance = get_distance_to_restaurant(restaurant.address, order.address, locations)
            order.possibly_restaurants = sorted(common_restaurants, key=operator.attrgetter('distance'))

    orders = Order.objects.order_price().filter(order_status__in=['AC', 'BL', 'SO', 'NO']).prefetch_related('order_items')
    restaurant_menu_items = RestaurantMenuItem.objects.all().select_related('product', 'restaurant')

    locations_data = [order.address for order in orders] + [restaurant.restaurant.address for restaurant in restaurant_menu_items]
    locations = Location.objects.filter(address__in=locations_data)

    get_sorted_by_distance_possibly_restaurants_to_cook(orders, restaurant_menu_items, locations)

    return render(request, template_name='order_items.html', context={
        'order_items': orders,
    })
