#!/bin/sh
if [ -f /opt/chatdev/runtime/sdk.py ]; then
  export CHATDEV_HOME=/opt/chatdev
fi
exec python -m company.worker "$@"
