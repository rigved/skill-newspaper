#!/bin/bash

##############################################################################
# update_certificates.sh
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
# Create the required folders and files
mkdir -p ../apiv1/secrets
touch ~/.rnd
# Generate the Root CA Key
openssl genrsa -out ../apiv1/secrets/rootCA.key 4096
# Generate the Root CA Certificate
openssl req -x509 -new -nodes \
    -key ../apiv1/secrets/rootCA.key \
    -sha512 \
    -days 36500 \
    -subj "/C=IN/ST=MH/O=Shield of Achilles CA/CN=shieldofachilles.in" \
    -reqexts v3_req -extensions v3_ca \
    -reqexts SAN \
    -config <(cat /etc/ssl/openssl.cnf <(printf "\n[SAN]\nsubjectAltName=DNS:shieldofachilles.in")) \
    -out ../apiv1/secrets/rootCA.crt
# Generate the private key for mycroftai.shieldofachilles.in
openssl genrsa -out ../apiv1/secrets/mycroftai.shieldofachilles.in.key 4096
# Generate the CSR for mycroftai.shieldofachilles.in
openssl req -new -sha512 \
    -key ../apiv1/secrets/mycroftai.shieldofachilles.in.key \
    -subj "/C=IN/ST=MH/O=Shield of Achilles/CN=mycroftai.shieldofachilles.in" \
    -reqexts SAN \
    -config <(cat /etc/ssl/openssl.cnf <(printf "\n[SAN]\nsubjectAltName=DNS:mycroftai.shieldofachilles.in,DNS:localhost")) \
    -out ../apiv1/secrets/mycroftai.shieldofachilles.in.csr
# Generate the certificate for mycroftai.shieldofachilles.in
openssl x509 -req \
    -in ../apiv1/secrets/mycroftai.shieldofachilles.in.csr \
    -CA ../apiv1/secrets/rootCA.crt \
    -CAkey ../apiv1/secrets/rootCA.key \
    -CAcreateserial \
    -days 36500 \
    -sha512 \
    -extfile <(printf "subjectAltName=DNS:mycroftai.shieldofachilles.in,DNS:localhost") \
    -out ../apiv1/secrets/mycroftai.shieldofachilles.in.crt
