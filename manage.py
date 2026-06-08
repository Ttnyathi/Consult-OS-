#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tkconsultancy.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Install it with `pip install django` or activate "
            "the virtual environment that has Django installed."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
