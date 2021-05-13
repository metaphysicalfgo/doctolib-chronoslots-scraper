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

If you are on OS X and want to use desktop notifications, please also check that you have `terminal-notifier`. 

You can install using brew `brew install terminal-notifier` or `gem install terminal-notifier -v 2.0.0`

## Usage

```
python3 main.py
python3 main.py --help
```

Supported parameters:
- `--limit` : change the number of pages of centers to browse (default is 5)
- `--city` : the city to search centers around (default is Paris)
- `--background` : this will make the script run until you stop it (availabilities on centers will be checked every minute)
- `--notify` : you can enable this parameter to get a toaster on your OS X device if slots are found
- `--auto_browse` : please do not use unless you are on MacOS with the Brave browser installed in the default application path (the only supported value is "Brave")

Please note that writing output as a csv file has been deprecated as data is very volatile and thus is not very relevant. 
