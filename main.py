import argparse
import csv
import json
from datetime import datetime
from functools import reduce
from random import choice

from multiprocessing import Pool, cpu_count, current_process, freeze_support
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
parser.add_argument("--output", default='output_$CITY_$DATE.txt', type=str, help="Output filename (available variables: $CITY, $DATE)")
parser.add_argument("--limit", type=int, default=20, help="Set the maximum number of Doctolib search pages")
parser.add_argument("--city", type=str, default="paris", help="The city to base the search on (default: Paris)")
parser.add_argument("--auto_browse", type=str, default="None", help="Experimental / DO NOT USE (works only with Brave on MacOS X")

args = parser.parse_args()
city = str.lower(args.city)
output = str(args.output).replace("$DATE", datetime.now().strftime("%Y%m%d%H%M%S")).replace("$CITY", city)

def random_headers():
    return {'User-Agent': choice(desktop_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}

def doctolib():
    results = []
    doctolib_url = "/vaccination-covid-19/{}?{}&ref_visit_motive_ids[]=6970&ref_visit_motive_ids[]=7005"
    doctolib_url_2 = "/vaccination-covid-19/{}?page={}&{}&ref_visit_motive_ids[]=6970&ref_visit_motive_ids[]=7005"

    max_nb_page = args.limit

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


def check_center_json_and_write_to_csv(url: str):
    conn = httpclient.HTTPSConnection(DOCTOLIB_URL)
    conn.request("GET", url)
    resp = conn.getresponse()
    resptext = resp.read().decode()
    respjson = json.loads(resptext)
    if("search_result" in respjson):
        with open(output, 'a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=",", quoting=csv.QUOTE_ALL)
            line_to_write = []
            line_to_write.append(respjson['total'])
            line_to_write.append(respjson['search_result']['city'])
            line_to_write.append(respjson['search_result']['last_name'])
            line_to_write.append("https://{}{}".format(DOCTOLIB_URL, respjson['search_result']['link']))
            csv_writer.writerow(line_to_write)


def scrape():
    start_time = datetime.now()

    print("Retrieving list of proximity centers...")
    results = doctolib()
    print()

    links = []
    for i in results:
        links.append(i['link'])

    items = len(links)
    units = min((cpu_count() - 1), items)
    print("Checking every centers for available slots...")
    with Pool(units):
        p_map(check_center_json_and_write_to_csv, links)
    print()
    stop_time_2 = datetime.now()

    # processing the results stored in the csv file in the doctolib directory
    res = []
    with open(output) as f:
        csv_reader = csv.reader(f, delimiter=",", quoting=csv.QUOTE_ALL)
        for line in csv_reader:
            res.append(line)

    total_with_slots = 0
    for centre in res:
        if int(centre[0]) > 0:
            total_with_slots += 1
            print("ALERT : {} slots available at {} ({}) => {}".format(centre[0], centre[2], centre[1], centre[3]))
            if args.auto_browse == "Brave":
                options = Options()
                options.binary_location = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
                driver_path = '/usr/local/bin/chromedriver'
                drvr = webdriver.Chrome(options = options, executable_path = driver_path)
                drvr.get(centre[3])

    print()
    print("Summary:")
    print(f"Total slots available : {total_with_slots}")
    print(f"Total browsed centers: {len(res)}")
    print(f"Total execution time: {(stop_time_2 - start_time)} seconds")

    if args.auto_browse != "None":
        input("Press Enter to continue...")
    

if __name__ == "__main__":
    scrape()
