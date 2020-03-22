#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiv1.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        error_string = "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        raise ImportError(error_string) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
