from django.contrib import admin

from caisse.models import (
    DetailMouvementCaisse,
    EcartCaisse,
    MouvementCaisse,
    SessionCaisse,
    TypeCaisse,
)

admin.site.register(TypeCaisse)
admin.site.register(SessionCaisse)
admin.site.register(EcartCaisse)
admin.site.register(DetailMouvementCaisse)
admin.site.register(MouvementCaisse)
