import os
import sys

# Forces the settings folder onto the system path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')

if ENVIRONMENT == 'production':
    from production import *
else:
    from base import *
