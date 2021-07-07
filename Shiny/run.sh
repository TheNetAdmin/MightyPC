#!/bin/bash

R -e "shiny::runApp('PowerPC/', port=32780, host='127.0.0.1')"
