# doctolib-chronoslots-scraper

[![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/60-percent-of-the-time-works-every-time.svg)](https://forthebadge.com)

## Description

This scraper can be used in an experimental way for people between 18 and 50 years old to find and register to an available vaccination slot in the next following days (what is commonly called a *chronodose*).

If you are not interested in scraping and just want to get a vaccine: please visit [ViteMaDose from covidtracker](https://vitemadose.covidtracker.fr) (which I am not affiliate to but like it very much), it is way (way) more user-centric 😊

## Installation

```
git clone https://github.com/metaphysicalfgo/doctolib-chronoslots-scraper.git
pip3 install -r requirements.txt
```

MacOS X users: 
- if want to use desktop notifications you will need "terminal-notifier", it can be installed using brew `brew install terminal-notifier` or `gem install terminal-notifier`
- if you want to try the "auto-open browser" feature, you will need the [chromedriver](https://chromedriver.chromium.org/), it can be installed through brew as well `brew install chromedriver`


## Usage

```
python3 main.py -h
```

Example:
```
python3 main.py --city marseille --limit 3 --background True
```

Supported parameters:
- `--limit` : change the number of pages of centers to browse (default is 5)
- `--city` : the city to search centers around (default is Paris)
- `--background` : this will make the script run until you stop it (availabilities on centers will be checked every minute)
- `--notify` : you can enable this parameter to get a toaster on your MacOS X device if slots are found
- `--auto_browse` : please do not use unless you are on MacOS X with the Brave browser installed in the default application path (the only supported value is "Brave")

Please note that writing output as a csv file has been deprecated as data is very volatile and thus is not very relevant. 
