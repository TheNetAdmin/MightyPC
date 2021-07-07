# MAG Scripts

This folder contails scripts to get publication info from Microsoft Academic Graph (MAG)

## 0. Get MAG Subscription Key

To use the MAG API, you should register a MAG subscription key, and hardcode it
into `mag.py:mag_client:sub_key`.

## 1. Get MAG Author ID for each PC Member

1. Prepare an input json file with basic PC member info, e.g. `input.json`
   ``` json
   [
       {
          "name": "Zixuan Wang",
          "email": "zxwang@ucsd.edu",
          "dblp": "",
          "dblp_origin": "",
          "google_scholar": "",
          "publication": [
              {
                  "title": "Characterizing and Modeling Non-Volatile Memory Systems"
              }
          ]
       }
   ]
   ```

   > - The only essential fields are `name`, `email` and `publication` (a list of
   dicts where each has at least on field called `title`)
   > - Other fields, e.g., `dblp`, `dblp_origin`, are not used when getting MAG ID,
   they are here for MICRO 2021 development process. You may modify function
   `mag.py:parse_author()` to remove the requirements of these fields.

2. Get MAG author id
   ``` bash
   python3 mag.py parse-author input.json mag.json -a
   ```

3. This generates an output file `mag.json` containing MAG Author ID for each member:
   ``` json
   {
       "Zixuan Wang": {
           "mag_id": 2922016956,
           "mag_name": "Zixuan Wang",
           "name": "Zixuan Wang",
           "email": "zxwang@ucsd.edu",
           "dblp": "",
           "dblp_origin": "",
           "google_scholar": ""
       }
   }
   ```

## 2. Download all publication records from MAG

Given an MAG Author ID, we can download all publications in MAG:

1. Run command
   ``` bash
   # Use a small number (e.g. 10) for -p argument for debugging and development
   # See code for more details
   python3 mag.py download-papers mag.json output -a -p 1000
   ```

2. This gives you full publication list for each pc member in `mag.json` file, and
   output to `output` dir, for e.g.:
   ```json
   [
       {
           "logprob": -18.063,
           "prob": 1.43000901e-08,
           "Id": 2921153466,
           "Ti": "basic performance measurements of the intel optane dc persistent memory module",
           "Y": 2019,
           "D": "2019-03-13",
           "CC": 148,
           "DN": "Basic Performance Measurements of the Intel Optane DC Persistent Memory Module.",
           "AA": [
               {
                   "DAuN": "Joseph Izraelevitz",
                   "AuN": "joseph izraelevitz",
                   "AuId": 2225246029,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Jian Yang",
                   "AuN": "jian yang",
                   "AuId": 2953500601,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Lu Zhang",
                   "AuN": "lu zhang",
                   "AuId": 2760996936,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Juno Kim",
                   "AuN": "juno kim",
                   "AuId": 2922515760,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Xiao Liu",
                   "AuN": "xiao liu",
                   "AuId": 2953993106,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Amirsaman Memaripour",
                   "AuN": "amirsaman memaripour",
                   "AuId": 2587459009,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Yun Joon Soh",
                   "AuN": "yun joon soh",
                   "AuId": 2921482178,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Zixuan Wang",
                   "AuN": "zixuan wang",
                   "AuId": 2922016956,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Yi Xu",
                   "AuN": "yi xu",
                   "AuId": 2921348835,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Subramanya R. Dulloor",
                   "AuN": "subramanya r dulloor",
                   "AuId": 2228692409,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Jishen Zhao",
                   "AuN": "jishen zhao",
                   "AuId": 2146366640,
                   "DAfN": "",
                   "AfId": null
               },
               {
                   "DAuN": "Steven Swanson",
                   "AuN": "steven swanson",
                   "AuId": 2193904605,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               }
           ],
           "F": [
               {
                   "DFN": "Computer data storage",
                   "FN": "computer data storage",
                   "FId": 194739806
               },
               {
                   "DFN": "DIMM",
                   "FN": "dimm",
                   "FId": 83401034
               },
               {
                   "DFN": "Non-volatile memory",
                   "FN": "non volatile memory",
                   "FId": 177950962
               },
               {
                   "DFN": "File system",
                   "FN": "file system",
                   "FId": 2780940931
               },
               {
                   "DFN": "Cache",
                   "FN": "cache",
                   "FId": 115537543
               },
               {
                   "DFN": "Dram",
                   "FN": "dram",
                   "FId": 7366592
               },
               {
                   "DFN": "Scalability",
                   "FN": "scalability",
                   "FId": 48044578
               },
               {
                   "DFN": "Interface (computing)",
                   "FN": "interface",
                   "FId": 108265739
               },
               {
                   "DFN": "Operating system",
                   "FN": "operating system",
                   "FId": 111919701
               },
               {
                   "DFN": "Computer science",
                   "FN": "computer science",
                   "FId": 41008148
               }
           ]
       },
       {
           "logprob": -19.458,
           "prob": 3.5440347e-09,
           "Id": 3103991664,
           "Ti": "characterizing and modeling non volatile memory systems",
           "Y": 2020,
           "D": "2020-10-01",
           "CC": 5,
           "DN": "Characterizing and Modeling Non-Volatile Memory Systems",
           "AA": [
               {
                   "DAuN": "Zixuan Wang",
                   "AuN": "zixuan wang",
                   "AuId": 2922016956,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Xiao Liu",
                   "AuN": "xiao liu",
                   "AuId": 2953993106,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Jian Yang",
                   "AuN": "jian yang",
                   "AuId": 2953500601,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Theodore Michailidis",
                   "AuN": "theodore michailidis",
                   "AuId": 3101582838,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Steven Swanson",
                   "AuN": "steven swanson",
                   "AuId": 2193904605,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Jishen Zhao",
                   "AuN": "jishen zhao",
                   "AuId": 2146366640,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               }
           ],
           "F": [
               {
                   "DFN": "DIMM",
                   "FN": "dimm",
                   "FId": 83401034
               },
               {
                   "DFN": "Microarchitecture",
                   "FN": "microarchitecture",
                   "FId": 107598950
               },
               {
                   "DFN": "Non-volatile random-access memory",
                   "FN": "non volatile random access memory",
                   "FId": 34172316
               },
               {
                   "DFN": "Cache",
                   "FN": "cache",
                   "FId": 115537543
               },
               {
                   "DFN": "Embedded system",
                   "FN": "embedded system",
                   "FId": 149635348
               },
               {
                   "DFN": "Computer science",
                   "FN": "computer science",
                   "FId": 41008148
               },
               {
                   "DFN": "Non-volatile memory",
                   "FN": "non volatile memory",
                   "FId": 177950962
               }
           ]
       },
       {
           "logprob": -20.319,
           "prob": 1.4982022e-09,
           "Id": 3165152505,
           "Ti": "characterizing and modeling nonvolatile memory systems",
           "Y": 2021,
           "D": "2021-05-01",
           "CC": 0,
           "DN": "Characterizing and Modeling Nonvolatile Memory Systems",
           "AA": [
               {
                   "DAuN": "Zixuan Wang",
                   "AuN": "zixuan wang",
                   "AuId": 2922016956,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Xiao Liu",
                   "AuN": "xiao liu",
                   "AuId": 2953993106,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Jian Yang",
                   "AuN": "jian yang",
                   "AuId": 3166556230,
                   "DAfN": "Google",
                   "AfN": "google",
                   "AfId": 1291425158
               },
               {
                   "DAuN": "Theodore Michailidis",
                   "AuN": "theodore michailidis",
                   "AuId": 3101582838,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Steven Swanson",
                   "AuN": "steven swanson",
                   "AuId": 2193904605,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               },
               {
                   "DAuN": "Jishen Zhao",
                   "AuN": "jishen zhao",
                   "AuId": 2146366640,
                   "DAfN": "University of California, San Diego",
                   "AfN": "university of california san diego",
                   "AfId": 36258959
               }
           ],
           "F": [
               {
                   "DFN": "DIMM",
                   "FN": "dimm",
                   "FId": 83401034
               },
               {
                   "DFN": "Microarchitecture",
                   "FN": "microarchitecture",
                   "FId": 107598950
               },
               {
                   "DFN": "Non-volatile random-access memory",
                   "FN": "non volatile random access memory",
                   "FId": 34172316
               },
               {
                   "DFN": "Systems design",
                   "FN": "systems design",
                   "FId": 31352089
               },
               {
                   "DFN": "Modular design",
                   "FN": "modular design",
                   "FId": 101468663
               },
               {
                   "DFN": "Scalability",
                   "FN": "scalability",
                   "FId": 48044578
               },
               {
                   "DFN": "Server",
                   "FN": "server",
                   "FId": 93996380
               },
               {
                   "DFN": "Embedded system",
                   "FN": "embedded system",
                   "FId": 149635348
               },
               {
                   "DFN": "Reverse engineering",
                   "FN": "reverse engineering",
                   "FId": 207850805
               },
               {
                   "DFN": "Computer science",
                   "FN": "computer science",
                   "FId": 41008148
               }
           ]
       }
   ]
   ```

## 3. Import to MongoDB

Use `MongoDB/import.py mag` to import the pc member MAG records
