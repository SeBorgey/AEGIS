#!/bin/bash
export OPENAI_API_KEY="AIzaSyA-gPoE6D2hsyUDdJsSuxRvYx-sTlK12W4"
python -u run_judge.py 2>&1 | tee output.log
