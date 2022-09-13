import csv
import json

# Function to convert a CSV to JSON
# Takes the file paths as arguments
def make_json():
    csvFilePath = r'micro2022-users.csv' 
    jsonFilePath = r'micro2022-users_dblp.json' 
    # create a dictionary
    data = {}
     
    # Open a csv reader called DictReader
    with open(csvFilePath, encoding='utf-8') as csvf:
        csvReader = csv.DictReader(csvf)
         
        # Convert each row into a dictionary
        # and add it to data
        for rows in csvReader:
            # Assuming a column named 'name' to
            # be the primary key
            key = rows['name']
            data[key] = rows
 
    # Open a json writer, and use the json.dumps()
    # function to dump data
    with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(data, indent=4))
         
if __name__ == "__main__":
    make_json()