#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}
strings /dev/urandom | grep -o '[[:graph:]]' | head -n 128 | tr -d '\n' | head -c 64 | xargs -0 -I{} ./update_superuser_password.exp {}
cd ../apiv1/
source /opt/venvs/mycroft-core/bin/activate
python manage drf_create_token -r mycroftai
