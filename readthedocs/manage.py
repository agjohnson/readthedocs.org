#!/usr/bin/env python3

import settings.sqlite
from django.core.management import execute_manager
execute_manager(settings.sqlite)
