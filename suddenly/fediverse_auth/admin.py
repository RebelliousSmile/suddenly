from django.contrib import admin

from .models import FediverseAccount, FediverseApp


@admin.register(FediverseApp)
class FediverseAppAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("instance", "software", "created_at")
    search_fields = ("instance",)
    readonly_fields = ("created_at",)


@admin.register(FediverseAccount)
class FediverseAccountAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("acct", "instance", "user", "created_at", "last_login_at")
    search_fields = ("acct", "instance", "user__username")
    readonly_fields = ("created_at", "last_login_at")
    raw_id_fields = ("user",)
