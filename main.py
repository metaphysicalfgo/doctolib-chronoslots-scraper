import argparse
import csv
import os
import signal
import json
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

parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=5, help="Set the maximum number of Doctolib search pages")
parser.add_argument("--city", type=str, default="paris", help="The city to base the search on (default: Paris)")
parser.add_argument("--auto_browse", type=str, default="None", help="WARN: currently only works with Brave on OS X")
parser.add_argument("--background", type=bool, default=False, help="Background mode")
parser.add_argument("--notify", type=bool, default=False, help="WARN: currently only works on OS X")

args = parser.parse_args()

def random_headers():
    return {'User-Agent': choice(desktop_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}

def os_notify(title, subtitle, message):
    t = '-title {!r}'.format(title)
    s = '-subtitle {!r}'.format(subtitle)
    m = '-message {!r}'.format(message)
    os.system('terminal-notifier {}'.format(' '.join([m, t, s])))

def handler(signum, frame):
    print("Thanks for using me. Bye.")
    exit(1)
 
signal.signal(signal.SIGINT, handler)

def get_centers(city, limit):
    results = []
    doctolib_url = "/vaccination-covid-19/{}?{}&ref_visit_motive_ids[]=6970&ref_visit_motive_ids[]=7005"
    doctolib_url_2 = "/vaccination-covid-19/{}?page={}&{}&ref_visit_motive_ids[]=6970&ref_visit_motive_ids[]=7005"
    max_nb_page = limit

    conn = httpclient.HTTPSConnection(DOCTOLIB_URL)
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


def retrieve_center_data(url: str):
    conn = httpclient.HTTPSConnection(DOCTOLIB_URL)
    conn.request("GET", url)
    resp = conn.getresponse()
    resptext = resp.read().decode()
    respjson = json.loads(resptext)
    if("search_result" in respjson):
        center_data = []
        center_data.append(respjson['total'])
        center_data.append(respjson['search_result']['city'])
        center_data.append(respjson['search_result']['last_name'])
        center_data.append("https://{}{}".format(DOCTOLIB_URL, respjson['search_result']['link']))
        return center_data


def process_center_availabilities_once(center_data_links, notify=False):
    proc_units = min((cpu_count() - 1), len(center_data_links))
    res = None
    with Pool(proc_units):
        res = p_map(retrieve_center_data, center_data_links)

    centers_with_slots = 0
    total_slots_found = 0
    for r in res:
        if int(r[0]) > 0:
            centers_with_slots += 1
            total_slots_found += int(r[0])
            print("ALERT:")
            print("       {} slots available at {} ({})".format(r[0], r[2], r[1]))
            print("       -> {}".format(r[3]))
            if args.auto_browse == "Brave":
                options = Options()
                options.binary_location = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
                driver_path = '/usr/local/bin/chromedriver'
                drvr = webdriver.Chrome(options = options, executable_path = driver_path)
                drvr.get(r[3])

    if args.notify:
        os_notify(title = 'Chronoslots scraper alert',
            subtitle = '{} slots founds on {} centers'.format(total_slots_found, centers_with_slots),
            message  = 'Check your terminal to clink on links!')


def scrape():
    start_time = datetime.now()

    print(f"Retrieving list of proximity centers around {args.city} with a limit of {args.limit} pages...")
    results = get_centers(city=str.lower(args.city), limit=args.limit)
    print()

    links = []
    for i in results:
        links.append(i['link'])
    nb_centers = len(links)

    iteration = 1
    print("[{}] {} : checking {} centers for available slots...".format(iteration, datetime.now(), nb_centers))
    process_center_availabilities_once(links)

    while args.background:
        print()
        print("...Waiting a minute before checking again...")
        print()
        time.sleep(60)
        iteration += 1
        print("[{}] {} : checking {} centers for available slots...".format(iteration, datetime.now(), nb_centers))
        process_center_availabilities_once(links)

    if args.auto_browse != "None":
        input("Press Enter to continue...")
    

if __name__ == "__main__":
    scrape()
