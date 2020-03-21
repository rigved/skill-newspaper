#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/../apiv1/
python manage.py migrate
python manage.py createsuperuser --username mycroftai --email mycroftai@localhost --noinput
