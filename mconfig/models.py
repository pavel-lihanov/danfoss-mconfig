from django.db import models
import uuid

# Create your models here.

from django.db import models

from django.contrib.auth.models import User

class Profile(models.Model):
    class Meta:
        #access modes:
        #   PM access: price details are shown (manufacturer price, delivery price, margin), delivery time is shown
        #   sales access: final price is shown, delivery time is shown
        #   authorized resellers: final price is shown, delivery time is shown? 
        #   anonymous: only typecode is shown
        #
        #   each order is assigned unique id, (id, price, date) is stored on server when creating offer file
        #   if matching entry in price list does not exist, give contact info
        #   order code should come from SAP (unique code is created for every new model ordered by a client)
        permissions = (
            ("register_users", "Can add sales users"),
            ("test", "Test permission"),
        )

    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    organization = models.CharField(max_length=60)
    email = models.EmailField(unique=True)    
    role = models.IntegerField()
    registered = models.BooleanField()
    user = models.OneToOneField(User, on_delete=models.CASCADE)

class Order(models.Model):
    class Meta:
        permissions = (
            ("view_all_orders", "Can see order list"),
            ("view_details", "Can see price details"),
            ("view_price", "Can view prices"),
            ("view_delivery", "Can view delivery time"),
        )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(auto_now_add=True)
    price_version = models.CharField(max_length=60)
    typecode = models.CharField(max_length=60)
    price = models.DecimalField(max_digits=12, decimal_places=3)
    user = models.ForeignKey(User)

