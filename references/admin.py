from django.contrib import admin
from .models import Region, Province, CityMunicipality, Barangay, Rank, AppBranding


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('name', 'code')


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('name', 'region')
    list_filter = ('region',)
    search_fields = ('name',)


@admin.register(CityMunicipality)
class CityMunicipalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province')
    list_filter = ('province__region',)
    search_fields = ('name',)


@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    list_display = ('name', 'city_municipality')
    search_fields = ('name',)
    autocomplete_fields = ('city_municipality',)


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ('rank_code', 'rank_desc', 'date_encoded', 'date_updated')
    search_fields = ('rank_code', 'rank_desc')


@admin.register(AppBranding)
class AppBrandingAdmin(admin.ModelAdmin):
    list_display = ('name_code', 'name_desc')
