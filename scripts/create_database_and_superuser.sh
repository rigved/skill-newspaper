#!/bin/bash

cd ../apiv1/
python manage.py migrate
python manage.py createsuperuser --username mycroftai --email mycroftai@localhost --noinput
