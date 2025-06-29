#!/bin/bash
source /home/saltchicken/workspace/trader/.venv/bin/activate
cd /home/saltchicken/workspace/trader
python src/trader/daily_update.py >>daily_update.log 2>&1
