#!/bin/bash

strings /dev/urandom | grep -o '[[:graph:]]' | head -n 128 | tr -d '\n' | head -c 64 | xargs -0 -I{} ./scripts/update_superuser_password.exp {}
cd ../apiv1/
python manage.py drf_create_token -r mycroftai
