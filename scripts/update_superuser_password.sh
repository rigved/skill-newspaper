#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/../apiv1/
source /opt/venvs/mycroft-core/bin/activate
python manage changepassword mycroftai
