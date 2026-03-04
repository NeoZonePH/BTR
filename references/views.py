from django.http import JsonResponse
from .models import Region, Province, CityMunicipality, Barangay, Rcdg, Cdc


def get_regions(request):
    """Return all regions."""
    regions = Region.objects.all().values('id', 'code', 'name')
    return JsonResponse(list(regions), safe=False)


def get_provinces(request):
    """Return provinces filtered by region."""
    region_id = request.GET.get('region_id')
    if region_id:
        provinces = Province.objects.filter(region_id=region_id).values('id', 'name')
    else:
        provinces = Province.objects.none()
    return JsonResponse(list(provinces), safe=False)


def get_cities(request):
    """Return cities/municipalities filtered by province."""
    province_id = request.GET.get('province_id')
    if province_id:
        cities = CityMunicipality.objects.filter(province_id=province_id).values('id', 'name')
    else:
        cities = CityMunicipality.objects.none()
    return JsonResponse(list(cities), safe=False)


def get_barangays(request):
    """Return barangays filtered by city/municipality."""
    city_id = request.GET.get('city_id')
    if city_id:
        barangays = Barangay.objects.filter(city_municipality_id=city_id).values('id', 'name')
    else:
        barangays = Barangay.objects.none()
    return JsonResponse(list(barangays), safe=False)


def get_rcdgs(request):
    """Return all RCDGs."""
    rcdgs = Rcdg.objects.all().order_by('rcdg_desc').values('id', 'rcdg_desc')
    return JsonResponse(list(rcdgs), safe=False)


def get_cdcs(request):
    """Return CDCs filtered by RCDG."""
    rcdg_id = request.GET.get('rcdg_id')
    if rcdg_id:
        cdcs = Cdc.objects.filter(rcdg_id=rcdg_id).order_by('cdc_desc').values('id', 'cdc_code', 'cdc_desc')
    else:
        cdcs = Cdc.objects.none()
    return JsonResponse(list(cdcs), safe=False)
