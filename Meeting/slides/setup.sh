#!/bin/bash

# Download the template from GitHub:
#    https://github.com/elauksap/focus-beamertheme
# This template is licensed in GPL-3.0, not compatible with current MIT license
# So we use this script to clone it before using

set -e
set -x

git clone https://github.com/elauksap/focus-beamertheme.git template
cd template || exit 2
# Checkout the version of this beamer template when developing ``../slides.py`
git checkout v2.8.1

# Install TeX packages required by this template
tlmgr install appendixnumberbeamer fira pgf
