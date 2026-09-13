#!/bin/sh
# Run from repository root on Ubuntu. Only E5 receives the private key.
set -eu
umask 077
if [ -e .deploy/tls ] || [ -e .deploy/config/e5-ca.crt ]; then
  echo 'Existing E5 TLS material found; refusing to replace it.' >&2
  exit 1
fi
mkdir -p .deploy/tls .deploy/config .deploy/evidence
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 365 \
  -keyout .deploy/tls/server.key -out .deploy/tls/server.crt \
  -subj '/CN=gavin-internal-e5' \
  -addext 'subjectAltName=IP:172.30.71.30' \
  -addext 'extendedKeyUsage=serverAuth'
cp .deploy/tls/server.crt .deploy/config/e5-ca.crt
# API/Worker run as 10001; config includes no provider secrets or private key.
chown -R 10001:10001 .deploy/tls .deploy/config .deploy/evidence
chmod 755 .deploy
chmod 750 .deploy/tls .deploy/config .deploy/evidence
chmod 640 .deploy/tls/server.key .deploy/tls/server.crt .deploy/config/e5-ca.crt
echo 'Internal E5 TLS created. Record the CA SHA-256 in the deployment profile.'
