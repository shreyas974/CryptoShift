#!/bin/sh
# SYNTHETIC fixture: key rotation helper
set -eu
openssl genrsa -out /tmp/svc.key 3072
openssl ecparam -genkey -name prime256v1 -out /tmp/ec.key
openssl dhparam -out /tmp/dh.pem 2048
ssh-keygen -t rsa -b 2048 -N "not-a-real-passphrase" -f /tmp/deploy_key
ssh-keygen -t ed25519 -f /tmp/deploy_ed
openssl genpkey -algorithm ML-DSA-65 -out /tmp/pqc.key
echo "run: openssl genrsa 2048"   # HN echo
openssl rand -hex 16              # HN not a key/algorithm choice
# openssl dgst -md5 file          # HN comment
which openssl ssh-keygen          # HN
