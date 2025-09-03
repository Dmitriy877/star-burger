from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum, F
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.conf import settings

import requests
from environs import Env
from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem
from geopy import distance
import operator


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

    def fetch_coordinates(apikey, address):
        base_url = "https://geocode-maps.yandex.ru/1.x"
        response = requests.get(base_url, params={
            "geocode": address,
            "apikey": apikey,
            "format": "json",
        })
        response.raise_for_status()
        found_places = response.json()['response']['GeoObjectCollection']['featureMember']

        if not found_places:
            return None

        most_relevant = found_places[0]
        lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
        return lat, lon

    def get_distance_to_restaurant(restaurant_address, delivery_address, api_key):
        try:
            restaurant_coordinates = fetch_coordinates(api_key, restaurant_address)
            delivery_coordinates = fetch_coordinates(api_key, delivery_address)
            return round(distance.distance(restaurant_coordinates, delivery_coordinates).km, 2)
        except Exception:
            return 'Произошла ошибка при получении геолокации'

    def get_common_restaurants(restaurants):
        common_restaurants = restaurants[0]
        for s in restaurants[1:]:
            common_restaurants = common_restaurants.intersection(s)
        return list(common_restaurants)

    def get_sorted_by_distance_possibly_restaurants_to_cook(orders, YANDEX_API_KEY):
        restaurant_menu_items = RestaurantMenuItem.objects.all().select_related('product', 'restaurant')
        for order in orders:
            restaurants = []
            for product in order.order_items.all():
                possibly_restaurants = restaurant_menu_items.filter(product=product.product, availability=True)
                restaurants.append(set(restaurant.restaurant for restaurant in possibly_restaurants))
            common_restaurants = get_common_restaurants(restaurants)
            for restaurant in common_restaurants:
                restaurant.distance = get_distance_to_restaurant(order.address, restaurant.address, YANDEX_API_KEY)
        order.possibly_restaurants = sorted(common_restaurants, key=operator.attrgetter('distance'))

    YANDEX_API_KEY = settings.YANDEX_API_KEY
    orders = Order.objects.order_price().filter(order_status__in=['AC', 'BL', 'SO', 'NO']).prefetch_related('order_items')
    get_sorted_by_distance_possibly_restaurants_to_cook(orders, YANDEX_API_KEY)

    return render(request, template_name='order_items.html', context={
        'order_items': orders,
    })
