#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/../apiv1/
# Create the required folder
mkdir -p secrets
source /opt/venvs/mycroft-core/bin/activate
python manage migrate
python manage createsuperuser --username mycroftai --email mycroftai@localhost --noinput
