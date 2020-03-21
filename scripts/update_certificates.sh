#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Create the required folders and files
mkdir -p ${DIR}/../apiv1/secrets
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
