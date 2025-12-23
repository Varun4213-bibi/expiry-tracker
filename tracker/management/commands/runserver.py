import os
import sys
import time
import webbrowser
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    help = 'Starts the development server and opens the browser automatically.'

    def handle(self, *args, **options):
        # Get the address and port from options, default to 0.0.0.0 for better accessibility
        addrport = options.get('addrport', '0.0.0.0:8000')
        if ':' in addrport:
            addr, port = addrport.rsplit(':', 1)
        else:
            addr = addrport
            port = '8000'

        # Construct the URL - use localhost for browser opening
        protocol = 'https' if options.get('use_ssl') else 'http'
        url = f'{protocol}://localhost:{port}/'

        # Call the parent runserver command
        super().handle(*args, **options)

        # Wait a moment for the server to start
        time.sleep(2)

        # Open the browser
        try:
            webbrowser.open(url)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully opened {url} in your default browser.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not open browser automatically: {e}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Server is running at {url}')
            )
