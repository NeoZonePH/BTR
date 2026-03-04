"""
Management command to import Philippine address data from JSON.
Source: flores-jacob/philippine-regions-provinces-cities-municipalities-barangays (GitHub)
"""

import json
import os
from django.core.management.base import BaseCommand
from references.models import Region, Province, CityMunicipality, Barangay


class Command(BaseCommand):
    help = 'Import Philippine regions, provinces, cities/municipalities, and barangays from JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', type=str,
            default='references/ph_addresses.json',
            help='Path to the Philippine addresses JSON file',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Clear existing data before importing',
        )

    def handle(self, *args, **options):
        json_path = options['file']
        if not os.path.exists(json_path):
            self.stderr.write(self.style.ERROR(f'File not found: {json_path}'))
            return

        if options['clear']:
            self.stdout.write('Clearing existing address data...')
            Barangay.objects.all().delete()
            CityMunicipality.objects.all().delete()
            Province.objects.all().delete()
            Region.objects.all().delete()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stdout.write(f'Loading Philippine address data from {json_path}...')

        region_count = 0
        province_count = 0
        city_count = 0
        barangay_count = 0

        for region_code, region_data in data.items():
            region_name = region_data.get('region_name', '').strip()
            if not region_name:
                continue

            region, _ = Region.objects.get_or_create(
                code=region_code,
                defaults={'name': region_name},
            )
            region_count += 1
            self.stdout.write(f'  Region: {region_name}')

            province_list = region_data.get('province_list', {})
            for province_name, province_data in province_list.items():
                province_name = province_name.strip()
                province, _ = Province.objects.get_or_create(
                    name=province_name,
                    region=region,
                )
                province_count += 1

                municipality_list = province_data.get('municipality_list', {})
                # municipality_list is a dict: {"MUNI_NAME": {"barangay_list": [...]}}
                if isinstance(municipality_list, dict):
                    muni_items = municipality_list.items()
                else:
                    # Fallback if it's a list of dicts
                    muni_items = []
                    for item in municipality_list:
                        if isinstance(item, dict):
                            muni_items.extend(item.items())

                for muni_name, muni_data in muni_items:
                    muni_name = muni_name.strip()
                    city, _ = CityMunicipality.objects.get_or_create(
                        name=muni_name,
                        province=province,
                    )
                    city_count += 1

                    barangay_list = muni_data.get('barangay_list', [])
                    barangay_objects = []
                    for brgy_name in barangay_list:
                        brgy_name = brgy_name.strip()
                        if brgy_name:
                            barangay_objects.append(
                                Barangay(name=brgy_name, city_municipality=city)
                            )

                    if barangay_objects:
                        Barangay.objects.bulk_create(
                            barangay_objects, ignore_conflicts=True,
                        )
                        barangay_count += len(barangay_objects)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Imported: {region_count} regions, {province_count} provinces, '
            f'{city_count} cities/municipalities, {barangay_count} barangays.'
        ))
