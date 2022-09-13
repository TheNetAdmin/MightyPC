# Inputs:
# Paper/micro2022-data.json Taken from 'Paper information > JSON'
# Paper/papers/*.pdfs Taken from 'Documents > Submissions'
# DBLP/micro2022-users_dblp.json Manually obtained from 'Names and emails'
# MongoDB/micro2022-pcinfo.csv Taken from 'PC Info'
# MongoDB/micro2022-topics.csv Taken from 'Paper information > Topics'

# Provided the inputs above are satisfied properly, this scripts populates the MongoDB
# database completely and comes up with reviewer suggestions for each paper. Once all 
# the steps are completed, the Shiny app can be configured the correct credentials and
# deployed.

cd ../Paper/
python3 paper.py parse-hotcrp-info papers/ micro2022-data.json
source gen_makefile.sh
cd papers
make -j 10

cd ../../DBLP
python3 dblp.py download-publication -p micro2022-users_dblp.json -o micro2022-users_dblp_i.json

cd ../MongoDB/
python3 import.py dblp -f ../DBLP/micro2022-users_dblp_i.json --all_members
python3 import.py submission -d ../Paper/papers/ -s hotcrp:submission 
python3 import.py submission -d ../Paper/papers/ -s hotcrp:submission -f reference
python3 import.py pc-member -f micro2022-pcinfo.csv
python3 import.py submission-tag -t micro2022-topics.csv -s hotcrp:submission

python3 conflict.py find-chair-conflict-papers -s hotcrp:submission -p hotcrp:pc > chair_conflicts.log
python3 conflict.py check-author-in-conflict -s hotcrp:submission -m dblp:paper -p hotcrp:pc > author_conflicts.log
python3 submission.py check-pc-reference -s hotcrp:submission -m dblp:paper -p hotcrp:pc 
python3 submission.py suggest-reviewers -s hotcrp:submission -m dblp:paper -p hotcrp:pc

# Deploy via RSConnect and ShinyApps R services: run in R shell in the following fashion
# sudo R 
# Rshell$   library(rsconnect)
# Rshell$   rsconnect::setAccountInfo(name='XXXX', token='XXXX', secret='XXXX')
# Rshell$   deployApp("MightyPC/")