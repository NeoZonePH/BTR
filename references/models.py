from django.db import models


class Region(models.Model):
    """Philippine region."""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.name


class Province(models.Model):
    """Philippine province."""
    name = models.CharField(max_length=255)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='provinces')

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'region')

    def __str__(self):
        return self.name


class CityMunicipality(models.Model):
    """Philippine city or municipality."""
    name = models.CharField(max_length=255)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='cities_municipalities')

    class Meta:
        ordering = ['name']
        verbose_name = 'City / Municipality'
        verbose_name_plural = 'Cities / Municipalities'
        unique_together = ('name', 'province')

    def __str__(self):
        return self.name


class Barangay(models.Model):
    """Philippine barangay (smallest administrative division)."""
    name = models.CharField(max_length=255)
    city_municipality = models.ForeignKey(
        CityMunicipality, on_delete=models.CASCADE, related_name='barangays',
    )

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Barangays'
        unique_together = ('name', 'city_municipality')

    def __str__(self):
        return self.name

# Create model for RCDG
class Rcdg(models.Model):
    rcdg_desc = models.CharField(max_length=20, null=False, blank=False, unique=True)
    rcdg_address = models.CharField(max_length=200, null=False, blank=False)
    rcdg_commander = models.CharField(max_length=100, null=False, blank=False)
    cp_no = models.CharField(max_length=20, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=False)
    latitude = models.CharField(max_length=50, null=True, blank=False)
    # GeoJSON Feature (Polygon or MultiPolygon) for region boundary; drawn with polygon tool in settings
    boundary_geojson = models.JSONField(null=True, blank=True)
    time_encoded = models.TimeField(auto_now_add=True)
    date_encoded = models.DateField(auto_now_add=True)
    time_updated = models.TimeField(auto_now=True)
    date_updated = models.DateField(auto_now=True)

    def __str__(self):
        return self.rcdg_desc

    class Meta:
        verbose_name_plural = "RCDG"

class Cdc(models.Model):
    rcdg = models.ForeignKey(Rcdg, null=False, blank=False, on_delete=models.CASCADE)
    cdc_code = models.CharField(max_length=20, null=False, blank=False, unique=True)
    cdc_desc = models.CharField(max_length=60, null=True, blank=False, unique=True)
    cdc_address = models.CharField(max_length=200, null=True, blank=False)
    cdc_director = models.CharField(max_length=100, null=True, blank=False)
    cp_no = models.CharField(max_length=20, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=False)
    latitude = models.CharField(max_length=50, null=True, blank=False)
    time_encoded = models.TimeField(auto_now_add=True)
    date_encoded = models.DateField(auto_now_add=True)
    time_updated = models.TimeField(auto_now=True)
    date_updated = models.DateField(auto_now=True)

    def __str__(self):
        return self.cdc_code

    class Meta:
        verbose_name_plural = "CDC"


class Rank(models.Model):
    """Military or organizational rank reference."""
    rank_code = models.CharField(max_length=20, unique=True)
    rank_desc = models.CharField(max_length=255)
    time_encoded = models.TimeField(auto_now_add=True)
    date_encoded = models.DateField(auto_now_add=True)
    time_updated = models.TimeField(auto_now=True)
    date_updated = models.DateField(auto_now=True)

    class Meta:
        ordering = ['rank_code']
        verbose_name_plural = 'Ranks'

    def __str__(self):
        return self.rank_desc or self.rank_code
