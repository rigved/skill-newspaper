#!/bin/bash

##############################################################################
# update_password_and_token.sh
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
cd ${DIR}
strings /dev/urandom | grep -o '[[:graph:]]' | head -n 128 | tr -d '\n' | head -c 64 | xargs -0 -I{} ./update_superuser_password.exp {}
cd ../apiv1/
source /opt/venvs/mycroft-core/bin/activate
python manage drf_create_token -r mycroftai
