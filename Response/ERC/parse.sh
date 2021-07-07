#!/bin/bash

set -e
set -x

parse="python3 ../survey.py"

$parse parse ERC_Survey.tsv ERC_Survey.json
$parse fix-name ERC_Survey.json \
    -o ERC_Survey_Fixed.json \
    -n "Timothy Sherwood"       "Tim Sherwood"                  \
    -n "Nikoleris Nikos"        "Nikos Nikoleris"               \
    -n "Khaled Khasawneh"       "Khaled N. Khasawneh"           \
    -n "Chia-Lin Yang"          "CHIA-LIN YANG"                 \
    -n "Shaizeen"               "Shaizeen Aga"                  \
    -n "Bronis R. de Supinski"  "Bronis de Supinski"            \
    -n "Niranjan Soundararajan" "Niranjan K Soundararajan"      \
    -n "Daniel"                 "Daniel Wong"                   \
    -n "Dan Sorin"              "Daniel Sorin"                  \
    -n "Abdel-Hameed (Hameed)"  "Abdel-Hameed (Hameed) Badawy"  \
    -n "Eugene John"            "Eugene B. John"                \
    -n "EJ (Eun Jung) Kim"      "Eun Kim"                       \
    -n "jeffrey stuecheli"      "Jeff Stuecheli"                \
    -n "Vignyan Kothinti"       "Vignyan Reddy Kothinti Naresh" \
    -n "Rob Bell"               "Robert Bell"                   \
    -n "Frank McKeen"           "Frank Mckeen"                  \
    -n "Alex Rico"              "Alejandro Rico"                \
    -n "Mullins"                "Robert Mullins"                \
    -n "Chris Hughes"           "Christopher Hughes"            \
    -n "Steve Keckler"          "Stephen W. Keckler"            \
    -n "Per"                    "Per Stenström"                 \
    -n "Per Stenstrom"          "Per Stenström"                 \
    -n "Josué Feliu"            "Josué Feliu Pérez"             \
    -n "Clay Hughes"            "Clayton Hughes"                \
    -n "SHUANG SONG"            "Shuang Song"                   \
    -n "Mahmut Kandemir"        "Mahmut Taylan Kandemir"        \
    -n "Elsasser"               "Wendy Elsasser"                \
    -n "Mahdi Bojnordi"         "Mahdi Nazm Bojnordi"           \
    -n "CHEN LI"                "Chen Li"                       \
    -n "Mike Ferdman"           "Michael Ferdman"               \
    -n "Drew Hilton"            "Andrew D. Hilton"              \
    -n "Jichuan"                "Jichuan Chang"                 \
    -n "Daniel R Johnson"       "Daniel Johnson"                \
;
$parse add-email ERC_Survey_Fixed.json ERC_Members.csv \
    -o ERC_Survey_Fixed_Email.json
$parse check-duplicate ERC_Survey_Fixed_Email.json \
    -o ERC_Survey_Dedup.json
$parse check-no-response ERC_Survey_Dedup.json ERC_Members.csv

mv ERC_Survey_Dedup.json dedup.json
rm ERC_Survey*.json
mv dedup.json ERC_Survey_Dedup.json