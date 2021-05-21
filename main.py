import argparse
import os
import sys
import signal
import json
import unicodedata
from datetime import datetime
import time
from functools import reduce
from random import choice

from multiprocessing import Pool, cpu_count, current_process, freeze_support
from types import resolve_bases
from tqdm import tqdm
from p_tqdm import p_map 

import http.client as httpclient

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from plyer import notification


import ssl
ssl._create_default_https_context = ssl._create_unverified_context

desktop_agents = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) '
    'AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'
]

DOCTOLIB_URL = "www.doctolib.fr"
DOCTOLIB_CHRONODOSE_FILTER = "force_max_limit=2"
VACCINE_ICON = "{}/{}".format(os.path.dirname(os.path.realpath(__file__)), "vaccine_ico.ico")

parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=5, help="Set the maximum number of Doctolib search pages")
parser.add_argument("--city", type=str, default="paris", help="The city to base the search on (default: Paris)")
parser.add_argument("--auto_browse", type=str, default="None", help="WARN: currently only works with Brave on OS X")
parser.add_argument("--background", type=bool, default=False, help="Background mode")
parser.add_argument("--notify", type=bool, default=False, help="WARN: currently only works on OS X")

args = parser.parse_args()

conn = httpclient.HTTPSConnection(DOCTOLIB_URL)

def random_headers():
    return {'User-Agent': choice(desktop_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}

def os_notify(title, subtitle, message):
    if sys.platform == "linux" or sys.platform == "linux2":
        print("Linux notification not supported yet.")
    elif sys.platform == "darwin":
        t = '-title {!r}'.format(title)
        s = '-subtitle {!r}'.format(subtitle)
        m = '-message {!r}'.format(message)
        os.system('terminal-notifier {}'.format(' '.join([m, t, s])))
    elif sys.platform == "win32":
        notification.notify(title=title, message=subtitle, app_icon=VACCINE_ICON, timeout=5)
    
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def handler(signum, frame):
    global conn
    conn.close()
    print("Thanks for using me. Bye.")
    exit(1)
 
signal.signal(signal.SIGINT, handler)

def countdown(t):
    while t:
        print("...Waiting {} seconds before checking again...".format(t), end="\r")
        time.sleep(1)
        t -= 1
      
def get_centers(city, limit):
    global conn
    results = []
    doctolib_url = "/vaccination-covid-19/{}?{}&ref_visit_motive_ids[]=6970&ref_visit_motive_ids[]=7005"
    doctolib_url_2 = "/vaccination-covid-19/{}?page={}&{}&ref_visit_motive_ids[]=6970&ref_visit_motive_ids[]=7005"
    max_nb_page = limit

    conn.request("GET", doctolib_url.format(city, DOCTOLIB_CHRONODOSE_FILTER), headers=random_headers())
    resptext = conn.getresponse().read().decode()
    soup = BeautifulSoup(resptext, 'html5lib')

    max_page_to_req = 1
    for p in soup.findAll('a', attrs={"class": "seo-magical-link"}):
        if p.span.get_text() is not None:
            max_page_to_req = int(p.span.get_text())
            
    if max_page_to_req > max_nb_page:
        max_page_to_req = max_nb_page

    with tqdm(total=max_page_to_req, initial=0) as progress_bar:
        results = doctolib_link_finder(soup)
        progress_bar.update()
        for n in range(2, max_page_to_req + 1):
            conn.request("GET", doctolib_url_2.format(city, n, DOCTOLIB_CHRONODOSE_FILTER), headers=random_headers())
            resptext = conn.getresponse().read().decode()
            results = results + doctolib_link_finder(BeautifulSoup(resptext, 'html5lib'))
            progress_bar.update()

    return results


def doctolib_link_finder(soup_object):
    found_links = []
    for r in soup_object.select(".dl-search-result"):
        base_url = "https://{}/search_results/{}.json?ref_visit_motive_ids%5B%5D=6970&ref_visit_motive_ids%5B%5D=7005&search_result_format=json&{}"
        id_centre = (r['id'].split('-')[2])
        name = id_centre
        link = base_url.format(DOCTOLIB_URL, id_centre, DOCTOLIB_CHRONODOSE_FILTER)
        found_links.append({"engine": "doctolib", "name": name, "link": link})
    return found_links


def https_retrieve_center_data(url: str):
    # We must create a new instance of conn each time. See issue #3.
    conn = httpclient.HTTPSConnection(DOCTOLIB_URL)
    conn.request("GET", url)
    resp = conn.getresponse()
    resptext = resp.read().decode()
    if resptext is not None:
        respjson = json.loads(resptext)
        if("search_result" in respjson and int(respjson['total'])) > 0:
            return respjson


def process_center_availabilities_once(center_data_links, iteration, notify=False):
    print()
    print("[{}] {} : checking {} centers for available slots...".format(iteration, datetime.now(), len(center_data_links)))

    proc_units = min((cpu_count() - 1), len(center_data_links))
    res = None
    with Pool(proc_units):
        res = p_map(https_retrieve_center_data, center_data_links)

    total_slots_found = 0
    total_with_slots = 0
    for r in res:
        if r is not None and len(r) > 0:
            total_slots_found += int(r['total'])
            total_with_slots += 1
            print("ALERT:")
            print("\t{} slots available at {} ({} {})".format(
                    r['total'], 
                    r['search_result']['last_name'], 
                    r['search_result']['city'], 
                    r['search_result']['zipcode']))
            print("\t-> https://{}{}".format(
                    DOCTOLIB_URL, 
                    r['search_result']['url']))
            if args.auto_browse == "Brave":
                options = Options()
                options.binary_location = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
                driver_path = '/usr/local/bin/chromedriver'
                drvr = webdriver.Chrome(options = options, executable_path = driver_path)
                drvr.get(r[3])

    if args.notify and total_slots_found > 0:
        os_notify(
            title = 'Chronoslots scraper alert',
            subtitle = '{} slots founds on {} centers'.format(total_slots_found, total_with_slots),
            message  = 'Check your terminal to clink on links!'
        )

    print()


if __name__ == "__main__":
    print(f"Retrieving list of proximity centers around {args.city} with a limit of {args.limit} pages...")
    results = get_centers(city=strip_accents(str.lower(args.city)), limit=args.limit)

    links = []
    for i in results:
        links.append(i['link'])

    iteration = 1
    process_center_availabilities_once(links, iteration)

    while args.background:
        countdown(60)
        iteration += 1
        process_center_availabilities_once(links, iteration)

    if args.auto_browse != "None":
        input("Press Enter to continue...")
