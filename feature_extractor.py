import json
import os
import sys
import re
import nltk
import tldextract
import urllib2
import time
import dns
import dns.name
import dns.query
import dns.resolver
from collections import defaultdict
from pyquery import PyQuery as pq
import includes.typo_checker



def is_typo_domain(domain):
	"""
	Returns true if given domain is a typosquatting domain. Relies on reverse_typo_offline module.
	"""	
	return typochecker.is_typo_domain(domain)


def safe_division(a, b):
	"""
	Casts a and b to floats and calculates their quotient (a/b), while catching ZeroDivisionErrors.
	Returns either the resulting quotient or 0.0 in case of a ZeroDivisionError.
	"""
	try:
		return float(a) / float(b)
	except ZeroDivisionError:
		return 0.0


def extract_HAR_features(harfile):
	"""
	Opens a HAR file (JSON), extracts features from it and store them in a dict.
	Returns the dict with the features.
	"""
	har_features = {}
	har = json.loads(open(harfile).read())

	domain = har["log"]["pages"][0]["id"]
	# Extract domain
	ext = tldextract.extract(domain)
	domain = ext.domain + '.' + ext.suffix
	domainNoTLD = ext.domain
	# initialize variables
	domainStringSent, firstparty_data, thirdparty_data, firstparty_html, thirdparty_html, firstparty_requests, thirdparty_requests = 0, 0, 0, 0, 0, 0, 0

	for entry in har["log"]["entries"]:
		requestUrl = str(entry["request"]["url"])
		ext = tldextract.extract(requestUrl)
		requestDomain = ext.domain + '.' + ext.suffix
		# Check if the domainNoTLD is passed in the parameters of the request
		url_parameters = re.search('https?:\/\/.*\/(.*)', requestUrl)
		if url_parameters:
			if domainNoTLD in url_parameters.group(1):
				domainStringSent += 1
		# Check if this is a first-party request (Request domain == site domain)
		result = re.search('https?:\/\/(.*)\/.*', requestUrl)
		if result:
			if domain in result.group(1):
				# print requestUrl, 'is FIRST party request of size', entry["response"]["bodySize"]
				firstparty_requests += 1
				firstparty_data += int(entry["response"]["bodySize"])
				if entry["response"]["content"]["mimeType"]:
					mimeType = entry["response"]["content"]["mimeType"]
					if 'text' in mimeType or 'javascript' in mimeType:
						firstparty_html += entry["response"]["bodySize"]
			else:
				# print requestUrl, 'is THIRD party request of size', entry["response"]["bodySize"]
				thirdparty_requests += 1
				thirdparty_data += int(entry["response"]["bodySize"])
				if entry["response"]["content"]["mimeType"]:
					mimeType = entry["response"]["content"]["mimeType"]
					if 'text' in mimeType or 'javascript' in mimeType:
						thirdparty_html += entry["response"]["bodySize"]

	har_features['TP_DataRatio'] = safe_division(thirdparty_data, firstparty_data + thirdparty_data)
	har_features['TP_HtmlRatio'] = safe_division(thirdparty_html, firstparty_html + thirdparty_html)
	har_features['TP_RequestRatio'] = safe_division(thirdparty_requests, firstparty_requests + thirdparty_requests)

	har_features['domainStringSent'] = domainStringSent
	har_features['initialResponseSize'] = har["log"]["entries"][0]["response"]["bodySize"]
	har_features['initialResponseRatio'] = safe_division(har_features['initialResponseSize'], firstparty_data + thirdparty_data)

	return har_features


def analyze_href(filename, domain):
	"""
	Analyzes the links (href property from the anchor elements) of an HTML file, in terms of length and externality.
	Returns  #internal links, #external links, accumlated link length, #links and whether or not there is a link pointing to a subdirectory of the domain

	"""
	# Select anchor elements using PyQuery
	nLinks, linkLength, internalLinks, externalLinks, internalSubDir = 0.0, 0.0, 0.0, 0.0, 0.0
	d = pq(filename=filename)
	links = d('a')
	try:
		for a in links:
			if pq(a).attr('href') is not None:
				href = pq(a).attr('href')
				# Calculate the average length of the href strings
				nLinks += 1
				linkLength += len(href)
				# Determine is href link is internal or external
				if href.startswith('http://') or href.startswith('https://') or href.startswith('//'):
					ext = tldextract.extract(href)
					linkdomain = ext.domain + '.' + ext.suffix
					# href domain == site domain?
					if linkdomain in domain:
						internalLinks += 1
						if href.count('/') > 3:
							internalSubDir = 1
					else:
						externalLinks += 1
				else:
					internalLinks += 1
					if href.count('/') > 1:
						internalSubDir = 1

	except UnicodeDecodeError:
		print 'Encoding problems...'
	return (internalLinks, externalLinks, linkLength, nLinks, internalSubDir)


def analyze_src(filename, domain):
	"""
	Analyzes the sources (src property from elements) of an HTML file, in terms of length and externality.
	Returns  #internal sources, #external sources, accumlated sources length, #sources and whether or not there is a source pointing to a subdirectory of the domain

	"""
	nSrc, srcLength, internalSrc, externalSrc, internalSubDir = 0.0, 0.0, 0.0, 0.0, 0.0
	# Select elements having the SRC attribute using PyQuery
	d = pq(filename=filename)
	srcElements = d('[src]')
	try:
		for el in srcElements:
			if pq(el).attr('src') is not None:
				src = pq(el).attr('src')
				# Calculate the average length of the href strings
				nSrc += 1
				srcLength += len(src)
				# Determine is src link is internal or external
				if src.startswith('http://') or src.startswith('https://') or src.startswith('//'):
					ext = tldextract.extract(src)
					linkdomain = ext.domain + '.' + ext.suffix
					# href domain == site domain?
					if linkdomain in domain:
						internalSrc += 1
						if src.count('/') > 3:
							internalSubDir = 1
					else:
						externalSrc += 1
				else:
					internalSrc += 1
					if src.count('/') > 1:
						internalSubDir = 1
	except UnicodeDecodeError:
		print 'Encoding problems...'
	return (internalSrc, externalSrc, srcLength, nSrc, internalSubDir)


def find_redirection_code_in_html(filename):
	"""
	Returns the number of 'window.location' and 'http-equiv="refresh"' occurrences in a file.
	"""
	metaRefresh = 0
	if sum(line.lower().count('http-equiv="refresh"') for line in open(filename)) > 0:
		# print '******* META REFRESH FOUND ****'
		metaRefresh = 1

	windowLocation = 0
	if sum(line.lower().count('window.location') for line in open(filename)) > 0:
		# print '******* WINDOW.LOCATION FOUND ****'
		windowLocation = 1

	return (metaRefresh, windowLocation)


def analyze_text(filename):
	"""
	Extracts text from HTML page using i.a. NLTK and the text within anchor elements.
	Returns length textual content, length of textual content in links and the total length of the original HTML file.
	"""
	with open(filename) as f:
		temp = f.read()
	# htmlContent = UnicodeDammit(temp, is_html=True)
	rawHtmlContent = temp.decode('ascii', 'ignore').encode('utf8')
	# Removing noscript tags manually. NLTK doesn't do this
	htmlContent = re.sub(re.compile('<noscript>.*?</noscript>', re.DOTALL), '', rawHtmlContent)
	htmlContent = re.sub(re.compile('<noframes>.*?</noframes>', re.DOTALL), '', htmlContent)
	htmlContent = re.sub(re.compile('<!--.*?-->', re.DOTALL), '', htmlContent)
	htmlContent = re.sub(re.compile('<script.*?</script>', re.DOTALL), '', htmlContent)
	# Get the natural language present on the page
	textualContent = nltk.clean_html(htmlContent)
	# Remove all whitespace, to keep only textual characters
	textualContent = re.sub('\s+', ' ', textualContent).strip()

	# Extract all text from anchor elements using PyQuery
	d = pq(htmlContent)
	links = d('a')
	linkTextualContent = ''
	try:
		for a in links:
			# Measure text of the anchor link
			if a.text is not None:
				text = a.text.encode('utf8')
				linkTextualContent += str(text)
		# Measure text inside the 'anchor blocks'
		for c in links.children():
			if c.text is not None:
				text = c.text.encode('utf8')
				linkTextualContent += str(text)
	except UnicodeDecodeError:
		print 'Encoding problems...'

	# Remove all whitespace, to keep only textual characters
	linkTextualContent = re.sub('\s+', ' ', linkTextualContent).strip()
	htmlContent = re.sub('\s+', ' ', htmlContent).strip()

	return (len(textualContent), len(linkTextualContent), len(rawHtmlContent))


def is_valid_website(foldername, sitefolder):
	"""
	Checks if the data gathered in the folder of this website failed.
	i.e. it checks for missing files, HTTP error codes, ...
	Returns True if data for this website is proper.
	"""
	if not os.path.isdir(foldername + '/' + sitefolder) or not os.path.isfile(foldername + '/' + sitefolder + '/HTML_' + sitefolder + '-root.htm'):
		return False
	with open(foldername + '/' + sitefolder + '/HTML_' + sitefolder + '-root.htm') as f:
		htmlString = str(f.read())
	with open(foldername + '/' + sitefolder + '/HAR_' + sitefolder + '.har') as f:
		harString = str(f.read())
	# Check the status code of the first returned response (check for 4xx or 5xx errors)
	regex = re.compile("\"status\": (\d)\d\d")
	r = regex.search(harString)
	if r is None:
		print '{{{ Could not find status string in HAR file }}}'
		return False
	else:
		if r.groups()[0] == '4' or r.groups()[0] == '5':
			print '{{{ 4xxx or 5xx error on this request. Skipping. }}}'
			return False
	if '<html><head></head><body></body></html>' in htmlString:
		print '{{{ Only default tag sequence found }}}'
		return False
	if htmlString is None:
		print '{{{ htmlstring is none }}}'
		return False
	if len(htmlString) < 250:  # Often these are errorneos pages, but they confuse our classifier
		print '{{{ htmlstring is too short }}}'
		return False
	return True


def write_header_to_file(foldername, featureDict):
	"""
	Writes the header string in to foldername + '_features.csv'
	"""
	with open(foldername + '_features.csv', 'w') as csvfile:
		firstHeader = True
		for key in sorted(featureDict.keys()):
			if not firstHeader:
				csvfile.write(',')
			else:
				firstHeader = False
			csvfile.write(str(key))
		csvfile.write('\n')


def append_features_to_file(foldername, featureDict):
	"""
	Write line with all the values of the dict.
	Also writes the header if called for the first time.
	"""
	if not os.path.isfile(foldername + '_features.csv'):
		write_header_to_file(foldername, featureDict)
	with open(foldername + '_features.csv', 'a') as csvfile:
		firstFeature = True
		for key in sorted(featureDict.keys()):
			if not firstFeature:
				csvfile.write(',')
			else:
				firstFeature = False
			csvfile.write(str(featureDict[key]))
		csvfile.write('\n')


def extract_website(foldername, sitefolder):
	"""
	Main method that will extract all features from the given website (folder.)
	Extracted features are written to a file
	"""
	featureDict = defaultdict(float)
	featureDict['Website'] = sitefolder
	featureDict['class'] = label
	if is_valid_website(foldername, sitefolder):
		print 'Extracting features from data of', str(sitefolder)
		if is_typo_domain(sitefolder):
			featureDict['typoDomain'] = 1
		else:
			featureDict['typoDomain'] = 0

		# Still need to initialize these one explicitly. Too bad. (in case they miss a file...)
		featureDict['mainFrameRedirects'] = 0
		featureDict['otherFrameRedirects'] = 0
		featureDict['differentFinalDomain'] = 0

		# Loop through all files, and extract data according to the file type
		for _file in os.listdir(foldername + '/' + sitefolder):
			# --HAR FILE--
			if _file.startswith('HAR_'):	
				har_features = extract_HAR_features(foldername + '/' + sitefolder + '/' + _file)
				# Copy over the HAR features dictionary to the main featureDict
				for key in sorted(har_features.keys()):
					featureDict[key] = har_features[key]

			# --MAIN FRAME REDIRECTS--
			elif _file.startswith('REDIRECTS-MAIN_'):
				with open(foldername + '/' + sitefolder + '/' + _file) as f:
					for i, l in enumerate(f):
						pass
				featureDict['mainFrameRedirects'] = i

			# --OTHER FRAME REDIRECTS--
			elif _file.startswith('REDIRECTS-FRAME_'):
				with open(foldername + '/' + sitefolder + '/' + _file) as f:
					for i, l in enumerate(f):
						pass
				featureDict['otherFrameRedirects'] = i

			# --FINAL URL FILE--
			elif _file.startswith('FINALURL_'):
				with open(foldername + '/' + sitefolder + '/' + _file) as f:
					final_url = f.readline().strip()
				ext = tldextract.extract(final_url)
				final_domain = ext.domain + '.' + ext.suffix
				if final_domain not in sitefolder:
					featureDict['differentFinalDomain'] = 1
				else:
					featureDict['differentFinalDomain'] = 0

			# --ALL HTML FILES--
			elif _file.startswith('HTML_'):
				# Initalize the temporary variables
				totalTextualContent, totalLinkTextualContent, totalHtmlContent = 0.0, 0.0, 0.0
				totalInternalLinks, totalExternalLinks, totalLinkLength, totalLinks = 0.0, 0.0, 0.0, 0.0
				totalInternalSrc, totalExternalSrc, totalSrcLength, totalSrc = 0.0, 0.0, 0.0, 0.0

				featureDict['frameCounter'] += 1
				(temp1, temp2, temp3) = analyze_text(foldername + '/' + sitefolder + '/' + _file)
				totalTextualContent += temp1
				totalLinkTextualContent += temp2
				totalHtmlContent += temp3

				(temp1, temp2, temp3, temp4, temp5) = analyze_href(foldername + '/' + sitefolder + '/' + _file, sitefolder)
				totalInternalLinks += temp1
				totalExternalLinks += temp2
				totalLinkLength += temp3
				featureDict['maxLinkLength'] = max(featureDict['maxLinkLength'], temp3)
				totalLinks += temp4
				if temp5 > 0:
					featureDict['internalSubDir'] = temp5
				else:
					# Might seem weird, but it is to ensure this value is present in the dict. (defaults to zero)
					featureDict['internalSubDir'] = featureDict['internalSubDir']

				(temp1, temp2, temp3, temp4, temp5) = analyze_src(foldername + '/' + sitefolder + '/' + _file, sitefolder)
				totalInternalSrc += temp1
				totalExternalSrc += temp2
				totalSrcLength += temp3
				totalSrc += temp4
				if temp5 > 0:
					featureDict['internalSubDir'] = temp5
				else:
					# Might seem weird, but it is to ensure this value is present in the dict. (defaults to zero)
					featureDict['internalSubDir'] = featureDict['internalSubDir']

				(temp1, temp2) = find_redirection_code_in_html(foldername + '/' + sitefolder + '/' + _file)
				featureDict['metaRefreshes'] += temp1
				featureDict['windowLocation'] += temp2

		# Ratio and average calculation (with division by zero check)
		featureDict['text2HtmlRatio'] = safe_division(totalTextualContent, totalHtmlContent)
		featureDict['link2TextRatio'] = safe_division(totalLinkTextualContent, totalTextualContent)
		featureDict['externalLinkRatio'] = safe_division(totalExternalLinks, totalInternalLinks + totalExternalLinks)
		featureDict['avgLinkLength'] = safe_division(totalLinkLength, totalLinks)
		featureDict['externalSrcRatio'] = safe_division(totalExternalSrc, totalInternalSrc + totalExternalSrc)
		featureDict['avgSrcLength'] = safe_division(totalSrcLength, totalSrc)
		if totalTextualContent - totalLinkTextualContent < 0:
			featureDict['nonLinkCharacters'] = 0
		else:
			featureDict['nonLinkCharacters'] = totalTextualContent - totalLinkTextualContent

		append_features_to_file(foldername, featureDict)

	else:
		print '=> Failed site -', str(sitefolder)

if __name__ == '__main__':
	# Checking arguments and print help message if necessary
	if len(sys.argv) != 3:
		print '### Incorrect number of arguments.'
		print '### USAGE: [Folder] [Class]'
		print '### EXAMPLE: python featureExtractor.py /Folder/With/WebsitesFolders/ benign'
		sys.exit()

	# Initializing the gloval typo_checker
	global typochecker
	typochecker = includes.typo_checker.TypoChecker()
	
	# Grabbing arguments
	foldername = sys.argv[1]
	if foldername.endswith('/'):
		foldername = foldername[:-1]
	label = sys.argv[2]

	# Delete previously created CSVs
	print 'Deleting previous feature files'
	if os.path.isfile(foldername + '_features.csv'):
		os.remove(foldername + '_features.csv')

	# Start extracting every website (folder)
	print 'Will write features to:', str(foldername + '_features.csv')
	for sitefolder in os.listdir(foldername):
		extract_website(foldername, sitefolder)