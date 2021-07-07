# MightyPC Web UI

This folder contains a web ui for program chair to quickly find a submission,
find the suggested reviewers and orther related info.

This web ui is written in R, runs on your local computer and connects to a
remote MongoDB, so you do not have to install and run it on the same machine
which runs MongoDB.

You should install R, RStudio and several related packages, see
`Shiny/MightyPC/app.R` to find which packages to install.

This web ui assumes some preset fields in MongoDB records, which you can generate
with other tools in the root repo. For e.g., to generate suggested pc members,
you may use `Paper/paper.py` to parse reference list for each submission, then
`MongoDB/submission.py suggest_reviewers` to suggest reviewers based on citations.

You may remove some data fields in `Shiny/MightyPC/app.R` if you do not need them,
for e.g. you may remove `submission_ml_suggested_reviewers` related code if you
do not have or need this data.
