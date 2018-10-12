from django.contrib import admin

import crossbot.models as models

admin.site.register(models.MiniCrosswordTime)
admin.site.register(models.CrosswordTime)
admin.site.register(models.EasySudokuTime)

admin.site.register(models.QueryShorthand)

class ItemOwnershipRecordInline(admin.TabularInline):
    model = models.ItemOwnershipRecord

class CBUserAdmin(admin.ModelAdmin):
    inlines = [
        ItemOwnershipRecordInline,
    ]

admin.site.register(models.CBUser, CBUserAdmin)
