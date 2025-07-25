import os
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    """
    Standalone test runner for the distributed system.
    Run this file directly to execute all tests.
    """
    
    # Setup Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    # Get the Django test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run tests with coverage and detailed output
    failures = test_runner.run_tests([
        "core",
        "wallet", 
        "inventory_service",
        "order_service"
    ])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        exit(1)
    else:
        print(f"\n✅ All tests passed!")
        exit(0)