from django.db import models
from django.core.validators import MinValueValidator
from django.core.validators import MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Sum, F
from django.utils import timezone


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50,
        null=False,
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
        null=False,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50,
        null=False,
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50,
        null=False,
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def order_price(self):
        order_price = (
            self.annotate(order_price=Sum(F('order_items__quantity') * F('order_items__price')))
        )
        return order_price


class Order(models.Model):
    ORDER_STATUS = {
        'AC': 'Заказ принят',
        'BL': 'Сборка заказа',
        'SO': 'Доставка заказа',
        'FN': 'Заказ завершен',
        'NO': 'Необработанный',
    }
    PAYMENT_METHOD = {
        'CASH': 'Наличными',
        'CARD': 'Электронно',
    }
    address = models.CharField('Адрес', max_length=256, null=False,)
    firstname = models.CharField('Имя', max_length=256, null=False,)
    lastname = models.CharField('Фамилия', max_length=256, null=False,)
    phonenumber = PhoneNumberField('Номер телефона', region='RU')
    objects = OrderQuerySet.as_manager()
    comment = models.TextField('Коментарий', max_length=450, default=' ')
    payment_method = models.CharField(
        'Способ оплаты',
        max_length=50,
        choices=PAYMENT_METHOD,
        default='CARD',
        db_index=True,
    )
    registrated_at = models.DateTimeField(
        'Заказ зарегестрирован',
        default=timezone.now,
        db_index=True,
    )
    called_at = models.DateTimeField(
        'Звонок выполнен',
        null=True,
        db_index=True,
        )
    delivered_at = models.DateTimeField(
        'Заказ доставлен',
        null=True,
        db_index=True,
    )
    order_status = models.CharField(
        'Статус заказа',
        max_length=2,
        choices=ORDER_STATUS,
        default='NO',
        db_index=True,
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы' 

    def __str__(self):
        return f"{self.firstname} {self.phonenumber}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='Товар'
    )
    quantity = models.IntegerField(
        'Количество',
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10),
        ]
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=None,
    )

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'

    def __str__(self):
        return f"{self.order} {self.product}"
