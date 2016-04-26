#!/usr/bin/bash

cat top-1m.csv | head -n 100 | tail -n 10 | cut -d',' -f2 | while read line; do
    echo "Retrieving $line"
    casperjs --folder=bening_samples --domain="$line" retrieve_page_data.js 
done
