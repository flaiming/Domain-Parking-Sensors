var fs = require('fs');
var casper = require('casper').create({
	viewportSize: {width: 1024, height: 768},
    onError: function(self, m) { // Any "error" level message will be written
            console.log('FATAL:' + m); // on the console output and PhantomJS will
            self.exit(); // terminate
        },
	//Initialize the object in a way to pretend to be a specific browser
	onPageInitialized : function(){
	 casper.evaluate(function () { 
	   		window.navigator = {
                appCodeName: 'Mozilla',
                appName: 'Netscape',
                cookieEnabled: true,
                vendor: 'Google Inc.',
                productSub : 20030107,
                product :'Gecko',
                platform : 'Win32',
                userAgent : 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36',
                appVersion : '5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36',
                doNotTrack : null,                           
            };       
    });
	}

}),
resources = []; // holds a list of resources of a particular page
casper.userAgent('Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36');


// This function recursively finds all (nested) frames on the web page and saves them to seperate HTML files.
var frameLevel = 'root';
function recursiveFrameScan() {
    fs.write(dataFolder + '/' + visiturl + '/HTML_' + visiturl + "-" + frameLevel + ".htm", casper.getHTML(), 'w');
    for(var i = 0; i < casper.page.framesCount; i++) {
        casper.page.switchToFrame(i);
        frameLevel = frameLevel + "-" + i.toString()
        casper.echo('Current Frame: ' + frameLevel);
        recursiveFrameScan();
        casper.page.switchToParentFrame();
        frameLevel = frameLevel.substring(0, frameLevel.length - (i.toString().length+1))
    }    
}

var domain = casper.cli.get("domain");
var dataFolder = casper.cli.get("folder");
var address = "http://" + domain;
visiturl = domain.replace(/\//g,"_");
    
// we keep track of when page start 
casper.on('load.started', function() {
    this.startTime = new Date();
});

// we keep track of when a resource is requested
casper.on('resource.requested', function(req) {
    resources[req.id] = {
        request: req,
        startReply: null,
        endReply: null
    };
});

// we keep track of when a resource is received
casper.on('resource.received', function(res) {
    if (res.stage === 'start') {
        resources[res.id].startReply = res;
    }
    if (res.stage === 'end') {
        resources[res.id].endReply = res;
    }    
});

// Record all rediretion hops
casper.on('navigation.requested', function(url, type, willNavigate, main) {
    console.log('> Trying to navigate to: ' + url + ' (main frame: ' + main + ')');
    // Check if the navigation resulted from a redirection
    if(type=="Other" || type=="Undefined") {
        // Check if it affects the main frame or another one
        if (main) {            
            // Main frame is redirecting. Logging to file.
            fs.write(dataFolder + '/' + visiturl + '/REDIRECTS-MAIN_' + visiturl + '.txt', url+'\n', 'a');
        }
        else {
            // Other frame is redirecting. Logging to file.
            fs.write(dataFolder + '/' + visiturl + '/REDIRECTS-FRAME_' + visiturl + '.txt', url+'\n', 'a');
        }
    }
});

// Open the webpage and retrieve the necessary data.
casper.start(address, function() {    
    this.echo('Opened: ' + address);
    this.endTime = new Date();
    var title = this.evaluate(function () {
        return document.title;
    });   

    this.echo('framesCount: ' + casper.page.framesCount);
    this.wait(10000, function() {
        // Create the HAR file using netsniff.js code (below)
        console.log('Creating HAR file.');
        har = createHAR(address, title, casper.startTime, resources);        
        fs.write(dataFolder + '/' + visiturl + '/HAR_' + visiturl + '.har', JSON.stringify(har, undefined, 4), 'w');        
        // Save all frames using the recursive frame scan
        console.log('Saving all frames.');  
        frameLevel = 'root';            
        recursiveFrameScan();        
        // Take a screenshot   
        console.log('Taking a screenshot of the page.'); 
        casper.capture(dataFolder + '/' + visiturl + '/SCRNSHT_' + visiturl + '.png');        
        // Log the final url of the web page
        console.log('Logging the final URL of the page.'); 
        var finalURL = this.evaluate(function () {return window.location.href;});        
        fs.write(dataFolder + '/' + visiturl + '/FINALURL_' + visiturl + '.txt', finalURL, 'w');

    });    
 
});

casper.run();



// netsniff.js for CapserJS
// Credits: 
// iroy2000 - https://github.com/iroy2000/casperjs-netsniff
// ariya - https://github.com/ariya/phantomjs/blob/master/examples/netsniff.js

/**
 * This code is a direct port of the version from PhantomJS, in order to have this script available in CasperJS as well
 * 
 * Note: 
 *  1) Developer can require 'fs' in order to write the har to file system directly
 *     This example only directly output the har object into the console
 * 
 *  2) Developer can easily modify the code so that it can parse a list of urls or the urls from your Casper tests
 *
 *  3) With the capability of CasperJS, this script could add web performance testing into Casper ( This script only is an example for proof of concept )
 *  
 *
 * Email: iroy2000 [at] gmail.com
 */

// make usre toISOString is available in Date object
if (!Date.prototype.toISOString) {
    Date.prototype.toISOString = function () {
        function pad(n) { return n < 10 ? '0' + n : n; }
        function ms(n) { return n < 10 ? '00'+ n : n < 100 ? '0' + n : n }
        return this.getFullYear() + '-' +
            pad(this.getMonth() + 1) + '-' +
            pad(this.getDate()) + 'T' +
            pad(this.getHours()) + ':' +
            pad(this.getMinutes()) + ':' +
            pad(this.getSeconds()) + '.' +
            ms(this.getMilliseconds()) + 'Z';
    }
}

/*
    creatHAR - create a har format object based on the parameter 
    @param  {String} address 
    @param  {String} title 
    @param  {String} startTime
    @param  {Array}  resources
    @return {Object} | JSON object for HAR viewer 
 */
function createHAR(address, title, startTime, resources)
{
    var entries = [];

    resources.forEach(function (resource) {
        var request = resource.request,
            startReply = resource.startReply,
            endReply = resource.endReply;

        if (!request || !startReply || !endReply) {
            return;
        }

        // Exclude Data URI from HAR file because
        // they aren't included in specification
        if (request.url.match(/(^data:image\/.*)/i)) {
            return;
    }

        entries.push({
            startedDateTime: request.time.toISOString(),
            time: endReply.time - request.time,
            request: {
                method: request.method,
                url: request.url,
                httpVersion: "HTTP/1.1",
                cookies: [],
                headers: request.headers,
                queryString: [],
                headersSize: -1,
                bodySize: -1
            },
            response: {
                status: endReply.status,
                statusText: endReply.statusText,
                httpVersion: "HTTP/1.1",
                cookies: [],
                headers: endReply.headers,
                redirectURL: "",
                headersSize: -1,
                bodySize: startReply.bodySize,
                content: {
                    size: startReply.bodySize,
                    mimeType: endReply.contentType
                }
            },
            cache: {},
            timings: {
                blocked: 0,
                dns: -1,
                connect: -1,
                send: 0,
                wait: startReply.time - request.time,
                receive: endReply.time - startReply.time,
                ssl: -1
            },
            pageref: address
        });
    });

    return {
        log: {
            version: '1.2',
            creator: {
                name: "PhantomJS",
                version: phantom.version.major + '.' + phantom.version.minor +
                    '.' + phantom.version.patch
            },
            pages: [{
                startedDateTime: startTime.toISOString(),
                id: address,
                title: title,
                pageTimings: {
                    onLoad: casper.endTime - casper.startTime
                }
            }],
            entries: entries
        }
    };
};
