#!/usr/bin/env bash

pip3 install youtube-dl

if [[ -z "${TG_CLIENT_SESSION_FILE}" ]] || [[ -z "${TG_CLIENT_SESSION_FILE_NAME}" ]]; then
  echo "No TG_CLIENT_SESSION_FILE env var, please specify it"
  exit 1
else
  echo "$TG_CLIENT_SESSION_FILE" | base64 -d > "${TG_CLIENT_SESSION_FILE_NAME}.session"
fi

exec ./YtbDownBot
