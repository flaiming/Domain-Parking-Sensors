# Domain Parking Sensors
These scripts can be used to extract features from web pages to build a classifier that can detect parked domains.

### Usage

 1. Retrieve the necessary data from a sample of domains (HAR, HTML, Redirections, frames, ...)
 
 ``` $ casperjs --domain=[somedomain.com] --folder=[output folder] retrieve_page_data.js```


 2. Extract 20+ features from this data (e.g. link location lengths, amount of text, third-party request ratio, ...)
 
 ``` $ python feature_extractor.py [folder] [class label]```

##### Example scenario

```sh
$ casperjs --domain=github.com --folder=benign_samples retrieve_page_data.js
$ casperjs --domain=stackoverflow.com --folder=benign_samples retrieve_page_data.js
...
$ casperjs --domain=giyhub.com --folder=parked_samples retrieve_page_data.js 
$ casperjs --domain=stackovreflow.com --folder=parked_samples retrieve_page_data.js 
...
```

 ```sh
$ python feature_extractor.py benign_samples benign
$ python feature_extractor.py parked_samples parked
```
