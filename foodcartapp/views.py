from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import requests

from .models import Product
from .models import Order
from .models import OrderItem
from .serializers import OrderSerializer
from locations.models import Location


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@api_view(['GET'])
def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return Response(dumped_products)


@api_view(['POST'])
def register_order(request):
    def create_location(apikey, address):

        location, created = Location.objects.get_or_create(address=address)

        if location.lat and location.lon:
            return location.lat, location.lon
        try:
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
            location.lon, location.lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
            location.save()
        except Exception:
            return None

    YANDEX_API_KEY = settings.YANDEX_API_KEY

    with transaction.atomic():

        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        address = serializer.validated_data['address']

        create_location(YANDEX_API_KEY, address)

        order = Order.objects.create(
            address=address,
            firstname=serializer.validated_data['firstname'],
            lastname=serializer.validated_data['lastname'],
            phonenumber=serializer.validated_data['phonenumber'],
            registrated_at=timezone.now()
        )

        for product in serializer.validated_data['products']:
            product = OrderItem.objects.create(
                order=order,
                product=product['product'],
                quantity=product['quantity'],
                price=product['product'].price * product['quantity']
            )

        return Response(OrderSerializer(order).data)
