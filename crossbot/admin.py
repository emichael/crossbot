import requests

from django.contrib import admin
from solo.admin import SingletonModelAdmin

import crossbot.models as models

admin.site.register(models.CrossbotSettings, SingletonModelAdmin)

admin.site.register(models.CBUser)

admin.site.register(models.MiniCrosswordTime)
admin.site.register(models.CrosswordTime)
admin.site.register(models.EasySudokuTime)

admin.site.register(models.QueryShorthand)

admin.site.register(models.Item)
admin.site.register(models.Hat)
admin.site.register(models.ItemOwnershipRecord)
