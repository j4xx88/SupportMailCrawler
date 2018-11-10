# E-Mail-crawler
# by Mark Schneemann
#
# Usage:
# python3 mail-crawler.py <crawling_depth> -u <target>
# python3 mail-crawler.py <crawling_depth> -l <list.csv>#
#
# Optional: add -v for verbose mode
#
# Examples:
# python3 mail-crawler.py 2 -u https://privacyscore.org
# python3 mail-crawler.py 3 -l lists/InstitutionsOfHigherEducation.csv
############################# Config ###############################

# Typical sites that contain email addresses.
# Everything is lowercase.
potential_sites_en = ["impressum", "support", "contact", "imprint",
    "team", "privacy", "police", "faq", "about", "help", "legal",
    "service"]
potential_sites_de = ["kontakt", "datenschutz", "über"]
potential_sites_debug = ["curriculum"]
potential_sites = potential_sites_en + potential_sites_de + potential_sites_debug

# Header of the crawler.
# Changed the User-Agent to old Mozilla - not everybody likes crawlers.
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
}

##### enable loader
from loaders.RequestsLoader import RequestsLoader
from loaders.SplashLoader import SplashLoader

# choose loader here:
# RequestsLoader - Loads html by just using requests.get
#   (fast but no js and rendering)
# SplashLoader - Loads rendered html by using a dockerized splash-browser
#   (slow but with js and rendering)
loader = SplashLoader

##### enabled parsers
# Cloudflare Protextion
from parsers.CloudflareParser import CloudflareParser
# a href="mailto...
from parsers.MailtoParser import MailtoParser
# regex for something@something.something
from parsers.RegexParser import RegexParser
# look for spoken chars like at or [at] instead of @
from parsers.SpokenEMailParser import SpokenEMailParser
# handle "javascript:linkTo_UnCryptMailto..."
from parsers.UncryptMailtoParser import UnCryptMailtoParser
parsers = [CloudflareParser, MailtoParser, RegexParser, SpokenEMailParser, UnCryptMailtoParser]
############################### Warning! ##########################
##################### Don't read below this line! #################
########################### Super ugly code! ######################

# import libraries
from bs4 import BeautifulSoup, SoupStrainer
import sys
import urllib.request
from urllib.request import Request, urlopen
import urllib
from urllib.parse import urlparse
import requests
import re
import argparse
import tldextract

VERBOSE = False

def build_url(baseurl, path):
    # Returns a list in the structure of urlparse.ParseResult
    url_parts = list(urllib.parse.urlparse(baseurl))
    url_parts[2] = path
    return urllib.parse.urlunparse(url_parts)

def get_promising_urls(soup, base):
    global VERBOSE
    global potential_sites


    found_sites = []
    for link in soup.find_all('a', href=True):
        for site in potential_sites:
            if link.string is not None and site in link.string.lower():
                # ToDo: rewrite this section!
                if link['href'] not in found_sites:
                    if VERBOSE:
                        print("\t\t'" + site + "' in '" + link.string.strip() + "'")
                    site = link['href']
                    if site.startswith("http://") or site.startswith("https://"):
                        check_this_site = site
                    elif site.startswith("mailto:"):
                        check_this_site = ""
                    elif site.endswith(".exe") or site.endswith(".pdf"):
                        # ToDo: exclude more filetypes
                        check_this_site = ""
                    elif site.startswith("//www."):
                        check_this_site = "https:" + site
                    else:
                        check_this_site = build_url(base, site)

                    # do not crawl other domains
                    base_domain = tldextract.extract(base).domain
                    check_domain = tldextract.extract(check_this_site).domain
                    if base_domain == check_domain:
                        found_sites.append(check_this_site)
    return found_sites

def get_promising_mails(soup):
    global VERBOSE
    global parsers
    email_addresses = set()
    for parser in parsers:
        email_addresses = email_addresses | parser.extract_mail_addresses(soup, VERBOSE)

    return email_addresses

def process_url(target):
    global VERBOSE
    global loader

    # check for redirects (thanks aok!)
    try:
        request = requests.get(target, allow_redirects=True, timeout=10)
        if len(request.history) > 0:
            target = request.url
            if VERBOSE:
                print("Redirected to: " + request.url)

        if VERBOSE:
            print("\nProcessing: " + target)
        email_addresses = set()
        links = []
        soup = loader.load_and_soup(target)
        email_addresses = get_promising_mails(soup)
        links= get_promising_urls(soup, target)
        return email_addresses, links
    except Exception:
        return set(), set()

def strip_emails(results):
    emails = set()
    for email in results:
        if email.startswith("mailto:"):
            emails.add(email[7:])
        elif email.startswith("mailto*"):
            emails.add(email[7:])
        elif email.startswith("regex:"):
            emails.add(email[6:])
        else:
            emails.add(email)
    return emails

def crawl(target, depth, done_urls):
    current_link = target
    emails = set()

    if int(depth) > 0:
        new_email_addresses, new_links = process_url(current_link)
        emails = emails.union(set(new_email_addresses))
        done_urls = done_urls.union(set([current_link]))
        for link in new_links:
            if link not in done_urls:
                done_urls, new_emails = crawl(link, int(depth)-1, done_urls)
                emails = emails.union(new_emails)

        emails = strip_emails(emails)
    return done_urls, emails

def filter_results_from_regex(emails):
    # filter results for regex errors
    results = []
    for e1 in emails:
        counter = 0
        for e2 in emails:
            if e2.startswith(e1):
                counter+=1
        if counter is 1:
            results.append(e1)
        else:
            if VERBOSE:
                print(e1 + " seems to be an regex related error.")
    return results

def Main():
    global VERBOSE

    parser = argparse.ArgumentParser()
    parser.add_argument("depth", help="Depth of the crawling-prozess. Should not be > 3", type=int)
    parser.add_argument("-u", "--url", help="URL of a site.", type=str)
    parser.add_argument("-l", "--list", help="List of a sites. Should be a PrivacyScore-Export.", type=str)
    parser.add_argument("-v", "--verbose", help="Verbose mode", action="store_true", default=False)
    args = parser.parse_args()

    VERBOSE = args.verbose

    if args.url:
        done_urls, emails = crawl(args.url, args.depth, set())
        if VERBOSE:
            print("\nResult:")

        results = filter_results_from_regex(emails)
        for email in sorted(results):
            print(email)
    if args.list:
        VERBOSE = False
        hits = 0
        file = open(args.list, "r")
        text = file.read()
        lines = text.split("\n")
        for i in range(1, len(lines) - 1):
            split_me = lines[i].split(";")
            url = split_me[0]
            done_urls, emails = crawl(url, args.depth, set())
            print(str(i) + "/" + str(len(lines) - 2) + "\t" + url + "\t" + str(len(emails)))
            if len(emails) > 0:
                hits += 1
                results = filter_results_from_regex(emails)
                for email in sorted(results):
                    print("\t\t" + email)
            else:
                print("\tNO HITS! TODO!")
        print(str(hits) + " of " + str(len(lines) - 2))

if __name__ == "__main__":
    Main()