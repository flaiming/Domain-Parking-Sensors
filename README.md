**DISCLAIMER: This code was forked from someone who then deleted the repo. It's not mine code.**

# Domain Parking Sensors

### Introduction
These scripts can be used to extract features from web pages to build a classifier that can detect parked domains.
The code is based on the research paper **"Parking Sensors: Analyzing and Detecting Parked Domains"** [[PDF]](http://www.internetsociety.org/doc/parking-sensors-analyzing-and-detecting-parked-domains) by Thomas Vissers, Nick Nikiforakis and Wouter Joosen. If you use, extend or build upon this project, we kindly ask you to cite the original NDSS paper. The relevant BibTeX is provided below.
 ```
@inproceedings{vissers2015parking,
 title={Parking Sensors: Analyzing and Detecting Parked Domains},
 author={Vissers, Thomas and Joosen, Wouter and Nikiforakis, Nick},
 booktitle={Proceedings of the ISOC Network and Distributed System Security Symposium (NDSS’15)},
 year={2015}
}
```

### Usage

 1. Retrieve the necessary data from a sample of domains (HAR, HTML, Redirections, frames, ...)
 
 ``` $ casperjs --folder=[output folder] --domain=[somedomain.com] retrieve_page_data.js```


 2. Extract 20+ features from this data (e.g. link location lengths, amount of text, third-party request ratio, ...)
 
 ``` $ python feature_extractor.py [folder] [class label]```

##### Example scenario

```sh
$ casperjs --folder=benign_samples --domain=github.com retrieve_page_data.js
$ casperjs --folder=benign_samples --domain=stackoverflow.com retrieve_page_data.js
...
$ casperjs --folder=parked_samples --domain=giyhub.com retrieve_page_data.js 
$ casperjs --folder=parked_samples --domain=stackovreflow.com retrieve_page_data.js 
...
```

 ```sh
$ python feature_extractor.py benign_samples benign
$ python feature_extractor.py parked_samples parked
```

### Requirements
 * **PhantomJS** (http://phantomjs.org/) - tested with version 1.9.7
 * **CasperJS** (http://casperjs.org/) - tested with version 1.1.0-beta3
 * **Python Modules** (```pip install -r requirements.txt```)


### Troubleshooting
Some versions of PhantomJS use SSLv3 by default. This might cause issues with SSL sites since the POODLE vulnerability was disclosed. To resolve this issue, you can add the following parameter when executing CasperJS:

```
--ssl-protocol=any 
```
 
More information:  http://stackoverflow.com/questions/26415188/casperjs-phantomjs-doesnt-load-https-page
