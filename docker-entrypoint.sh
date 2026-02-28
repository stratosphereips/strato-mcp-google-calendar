#!/bin/sh
set -e

case "$1" in
  auth)  exec google-calendar-auth ;;
  serve) exec google-calendar-mcp  ;;
  *)     exec "$@"                 ;;
esac
