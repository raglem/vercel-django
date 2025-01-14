from django.contrib import admin
from .models import Membership, PickupPlayer, PickupTeam, PickupGame

# Register your models here.
admin.site.register(Membership)
admin.site.register(PickupPlayer)
admin.site.register(PickupTeam)
admin.site.register(PickupGame)