#!/usr/bin/bash

cat parking_urls.txt | while read line; do
    echo "Retrieving $line"
    casperjs --folder=parked_samples --domain="$line" retrieve_page_data.js 
done
