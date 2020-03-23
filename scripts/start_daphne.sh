#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/../apiv1/
source /opt/venvs/mycroft-core/bin/activate
if [[ -f "secrets/mycroftai.shieldofachilles.in.key" ]] & [[ -f "secrets/mycroftai.shieldofachilles.in.crt" ]]; then
    daphne -e "ssl:65443:privateKey=secrets/mycroftai.shieldofachilles.in.key:certKey=secrets/mycroftai.shieldofachilles.in.crt" "apiv1.asgi:application"
else
    echo "Private key and Certificate files missing."
    exit 1
fi
