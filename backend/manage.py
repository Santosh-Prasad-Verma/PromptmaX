#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def load_environment():
    """Load root defaults first, then backend-local overrides."""
    from dotenv import load_dotenv

    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir.parent / '.env')
    load_dotenv(base_dir / '.env', override=False)


def main():
    """Run administrative tasks."""
    load_environment()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'promptx_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
