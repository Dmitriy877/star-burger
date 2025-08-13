from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response

import json
from .models import Product
from .models import Order
from .models import OrderItem


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

    data = request.data

    if 'products' not in data:
        return Response({
            'products': 'Обязательное поле'
        })
    elif (not isinstance(data['products'], list) and
          data['products'] is not None):
        return Response({
            'products': 'Ожидался list со значениями, но был получен "str"'
        })
    elif data['products'] is None:
        return Response({
            'products': 'Это поле не может быть пустым.'
        })
    elif not data['products']:
        return Response({
            'products': 'Этот список не может быть пустым.'
        })
    elif ('firstname' not in data and
          'lastname' not in data and
          'phonenumber' not in data and
          'address' not in data):
        return Response({
            'firstname, lastname, phonenumber, address': 'Обязательное поле.'
        })
    elif (data['firstname'] is None and
          data['lastname'] is None and
          data['phonenumber'] is None and
          data['address'] is None):
        return Response({
            'firstname, lastname, phonenumber, address': 'Это поле не может быть пустым.'
        })
    elif data['phonenumber'] == "":
        return Response({
            'phonenumber': 'Это поле не может быть пустым.'
        })
    elif data['phonenumber'][2] == '0':
        return Response({
            'phonenumber': 'Введен некорректный номер телефона.'
        })
    elif (not isinstance(data['firstname'], str) and
          data['firstname'] is not None):
        return Response({
            'firstname': 'Not a valid string.'
        })
    elif data['firstname'] is None:
        return Response({
            'firstname': 'Это поле не может быть пустым.'
        })
    for product in data['products']:
        try:
            product_id = product['product']
            Product.objects.get(id=product_id)
        except Exception:
            return Response({
                'products': f'Недопустимый первичный ключ {product_id}'
            })

    order = Order.objects.create(
        adress=data['address'],
        name=data['firstname'],
        last_name=data['lastname'],
        phone_number=data['phonenumber'],
    )

    for product in data['products']:
        OrderItem.objects.create(
            order=order,
            product=Product.objects.get(pk=product['product']),
            product_amount=product['quantity'],
        )
    return Response()
