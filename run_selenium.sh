#!/bin/bash

modus="standalone"

for ((i=1;i<=$#;i++)); 
do

    if [ ${!i} = "-m" ] 
    then ((i++)) 
        modus=${!i};
    fi

done;

declare -a acceptable_modi=("kubernetes" "compose" "standalone")

# Basic syntax:
if [[ "${acceptable_modi[*]}" =~ "${modus}" ]]; then
    echo "Starting Selenium in Modus $modus"
    if [[ $modus = "kubernetes" ]]; then
        kubectl apply -f ./k8s_selenium_grid.yml
    elif [[ $modus = "compose" ]]; then
        docker-compose up --remove-orphans -d
    elif [[ $modus = "standalone" ]]; then
        docker run -d -p 4444:4444 --shm-size="2g" selenium/standalone-firefox:latest
    fi
else
    echo "$modus not supported. Use [${acceptable_modi[@]}] instead"
fi

