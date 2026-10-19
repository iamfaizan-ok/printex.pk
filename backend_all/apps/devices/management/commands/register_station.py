import secrets
from django.core.management.base import BaseCommand
from apps.devices.models import PrintStation


class Command(BaseCommand):
    help = 'Registers or updates a Print Station credential for the Windows PC Print Agent'

    def add_arguments(self, parser):
        parser.add_argument('--code', type=str, default='STN-MAIN-01', help='Unique station code')
        parser.add_argument('--name', type=str, default='Main Print Facility Windows Station', help='Human readable station name')
        parser.add_argument('--secret', type=str, default='', help='Secret token for the agent. If omitted, generates random token.')
        parser.add_argument('--printers', type=str, default='HP LaserJet Pro M404n,Microsoft Print to PDF', help='Comma-separated allowed printer names')

    def handle(self, *args, **options):
        station_code = options['code']
        station_name = options['name']
        secret = options['secret'] or secrets.token_urlsafe(24)
        printers_list = [p.strip() for p in options['printers'].split(',') if p.strip()]

        station, created = PrintStation.objects.get_or_create(
            station_code=station_code,
            defaults={
                'name': station_name,
                'allowed_printers': printers_list,
                'capabilities': {
                    'paper_sizes': ['A4', 'A3', 'Letter', 'Legal'],
                    'colour': True,
                    'duplex': True,
                },
                'is_enabled': True,
                'status': 'offline',
            }
        )

        station.name = station_name
        station.allowed_printers = printers_list
        station.set_token(secret)
        station.is_enabled = True
        station.save()

        action = "Created new" if created else "Updated existing"
        self.stdout.write(self.style.SUCCESS(f"{action} Print Station successfully!"))
        self.stdout.write(f"Station Code : {station_code}")
        self.stdout.write(f"Agent Secret : {secret}")
        self.stdout.write(f"Printers     : {printers_list}")
        self.stdout.write(self.style.WARNING("Save this secret in your PC Print Agent config.py or .env file!"))
