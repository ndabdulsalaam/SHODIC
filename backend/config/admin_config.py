"""
RxChat Admin Site Configuration
Customises the Django admin header, title, and index title.
"""
from django.contrib import admin

admin.site.site_header = 'RxChat Administration'
admin.site.site_title = 'RxChat Admin'
admin.site.index_title = 'Dashboard'
