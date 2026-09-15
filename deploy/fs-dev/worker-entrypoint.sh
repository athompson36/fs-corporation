#!/bin/sh
if [ -f /opt/chatdev/runtime/sdk.py ]; then
  export CHATDEV_HOME=/opt/chatdev
fi
if [ -d /opt/chatdev/.venv ]; then
  _chatdev_sp=""
  if [ -d /opt/chatdev/.venv/lib/python3.12/site-packages ]; then
    _chatdev_sp="/opt/chatdev/.venv/lib/python3.12/site-packages"
  else
    for _py in /opt/chatdev/.venv/lib/python*/site-packages; do
      if [ -d "$_py" ]; then
        _chatdev_sp="$_py"
        break
      fi
    done
  fi
  if [ -n "$_chatdev_sp" ]; then
    if [ -n "$PYTHONPATH" ]; then
      export PYTHONPATH="${_chatdev_sp}:${PYTHONPATH}"
    else
      export PYTHONPATH="${_chatdev_sp}"
    fi
  fi
fi
exec python -m company.worker "$@"
