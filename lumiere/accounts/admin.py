from django.contrib import admin

from .models import Address, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "role", "is_active", "failed_attempts", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "name")
    fields = ("email", "name", "role", "is_active", "last_login", "date_joined", "failed_attempts", "locked_until")
    readonly_fields = ("last_login", "date_joined", "failed_attempts", "locked_until")
    actions = ["unlock_accounts"]

    @admin.action(description="Unlock selected accounts")
    def unlock_accounts(self, request, queryset):
        updated = queryset.update(failed_attempts=0, locked_until=None)
        self.message_user(request, f"{updated} account(s) unlocked.")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "street", "city", "state", "postal_code", "country")
    search_fields = ("customer__email", "street", "city", "postal_code")
