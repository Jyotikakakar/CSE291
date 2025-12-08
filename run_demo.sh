#!/bin/bash

if [ "$1" == "--all" ]; then
    rm -f meetings.db data/extracted_data.json
    python run.py
    echo ""
    echo "Order: alphabetical (mike_eng -> priya_design -> sarah_pm)"
else
    rm -f meetings.db data/extracted_data.json
    python run.py --user sarah_pm
    python run.py --user mike_eng
    python run.py --user priya_design
    echo ""
    echo "Order: sarah_pm -> mike_eng -> priya_design"
fi

