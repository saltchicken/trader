#!/bin/bash
source /home/saltchicken/workspace/trader/.venv/bin/activate
cd /home/saltchicken/workspace/trader
python src/trader/daily_update.py 2>&1 | systemd-cat -t daily_update
