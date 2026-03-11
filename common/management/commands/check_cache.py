"""Management command to verify Redis cache connectivity."""

from django.core.management.base import BaseCommand

from common.cache import cache_delete, cache_get, cache_set


class Command(BaseCommand):
    help = "Check Redis cache connection"

    def handle(self, *args, **options):
        key = "_cache_health_check_"
        expected = "ok"

        self.stdout.write("Testing cache connection...")

        ok = cache_set(key, expected, timeout=10)
        if not ok:
            self.stdout.write(self.style.ERROR("FAIL: cache_set returned False (Redis unavailable?)"))
            return

        value = cache_get(key)
        if value == expected:
            self.stdout.write(self.style.SUCCESS("Cache OK — Redis is reachable and working."))
        else:
            self.stdout.write(
                self.style.ERROR(f"FAIL: expected {expected!r}, got {value!r}")
            )

        cache_delete(key)
