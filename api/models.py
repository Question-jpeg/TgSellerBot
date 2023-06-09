from django.db import models


class Category(models.Model):
    title = models.CharField(max_length=255, verbose_name='Название')
    is_size = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self) -> str:
        return self.title


class UserInfo(models.Model):
    chat_id = models.IntegerField()
    size = models.CharField(max_length=5, null=True, blank=True)
    category = models.ForeignKey(to=Category, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_admin_interface = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.chat_id)

class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(to=Category, on_delete=models.PROTECT, related_name='products')
    price = models.IntegerField()

    def __str__(self) -> str:
        return self.title

class ProductSize(models.Model):
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField(max_length=5)

class ProductPhoto(models.Model):
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE, related_name='photos')
    photo_id = models.CharField(max_length=255)

class Config(models.Model):
    key = models.CharField(max_length=255)
    value = models.TextField()

    def __str__(self) -> str:
        return self.key

class ProductCreationCache(models.Model):
    user = models.ForeignKey(to=UserInfo, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(to=Category, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)

class ProductSizeCached(models.Model):
    product_cache = models.ForeignKey(to=ProductCreationCache, on_delete=models.CASCADE)
    size = models.CharField(max_length=5)

class ProductPhotoCached(models.Model):
    product_cache = models.ForeignKey(to=ProductCreationCache, on_delete=models.CASCADE)
    photo_id = models.CharField(max_length=255, null=True, blank=True)