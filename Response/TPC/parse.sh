#!/bin/bash

set -e
set -x

parse="python3 ../survey.py"

$parse parse TPC_Survey.tsv TPC_Survey.json
$parse fix-name TPC_Survey.json \
    -o  TPC_Survey_Fixed.json \
    -n "Dreslinski" "Ronald Dreslinski" \
    -n "Tony Gutierrez"         "Anthony Gutierrez"       \
    -n "Vijay"                  "Vijay Janapa Reddi"      \
    -n "Jagadish"               "Jagadish Kotra"          \
    -n "Mark Oskin"             "Mark Oskin"              \
    -n "Matthew Sinclair"       "Matthew D. Sinclair"     \
    -n "Yingyan (Celine) Lin"   "Yingyan Lin"             \
    -n "Murali"                 "Murali Annavaram"        \
    -n "Yiannakis Sazeides"     "Yanos Sazeides"          \
    -n "Osman Sabri Unsal"      "Osman Unsal"             \
    -n "Chunhao"                "Chunhao Wang"            \
    -n "Mike O’Connor"          "Mike O'Connor"           \
    -n "Benjamin Lee"           "Benjamin C. Lee"         \
    -n "Siva Hari"              "Siva Kumar Sastry Hari"  \
    -n "Dreslinski"             "Ronald Dreslinski"       \
    -n "Iris Bahar"             "Ruth Iris Bahar"         \
    -n "Trevor Carlson"         "Trevor E. Carlson"       \
    -n "yuan xie"               "Yuan Xie"                \
    -n "Hyesoon Kim"            "Kim Hyesoon"             \
    -n "Tushar"                 "Tushar Krishna"          \
    -n "Yatin Manerkar"         "Yatin A. Manerkar"       \
    -n "Gilles Pokam"           "Gilles A Pokam"          \
    -n "Yun Eric Liang"         "Yun Liang"               \
    -n "Tim Rogers"             "Timothy G. Rogers"       \
    -n "Alex Jones"             "Alex K. Jones"           \
;
$parse add-email TPC_Survey_Fixed.json TPC_Members.csv \
    -o TPC_Survey_Fixed_Email.json
$parse check-duplicate TPC_Survey_Fixed_Email.json \
    -o TPC_Survey_Dedup.json \
    -l "Dmitry Ponomarev" \
    -u "Divya Mahajan" \
    -l "Swamit Tannu" \
    -e "Christopher Fletcher" \
    -l "Pedro Trancoso"
$parse check-no-response TPC_Survey_Dedup.json TPC_Members.csv

mv TPC_Survey_Dedup.json dedup.json
rm TPC_Survey*.json
mv dedup.json TPC_Survey_Dedup.json