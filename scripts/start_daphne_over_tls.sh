#!/bin/bash

##############################################################################
# start_daphne_over_tls.sh
# Copyright (C) 2020  Rigved Rakshit
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
##############################################################################


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/../apiv1/
source /opt/venvs/mycroft-core/bin/activate
if [[ -f "secrets/mycroftai.shieldofachilles.in.key" ]] & [[ -f "secrets/mycroftai.shieldofachilles.in.crt" ]]; then
    daphne --endpoint "ssl:65443:privateKey=secrets/mycroftai.shieldofachilles.in.key:certKey=secrets/mycroftai.shieldofachilles.in.crt" "apiv1.asgi:application"
else
    echo "Private key and Certificate files missing."
    exit 1
fi
