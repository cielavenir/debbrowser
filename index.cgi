#!/usr/bin/env python3

from debian_parser import PackagesParser

import requests
import os
import sys
import re

import gzip
import bz2
import lzma

def create_table(titles, items):
    result = "<table><thead><tr>\n"
    for title in titles:
        result += "<th>" + title + "</th>\n"
    result += "</tr></thead><tbody>\n"
    for item in items:
        result += "<tr>\n"
        for e in item:
            result += "<td>" + e + "</td>\n"
        result += "</tr>\n"
    result += "</tbody></table>\n"
    return result

def main():
    # redirect to index.cgi if omitted
    if os.path.basename(__file__) not in os.environ["REQUEST_URI"].split("/"):
        # REQUEST_URI includes PATH_INFO, so this check is rough, but should be fine for now
        print("Status: 301 Found")
        print("Location: " + os.path.basename(__file__))
        print("")
        return

    pathInfo = os.environ.get("PATH_INFO", "")
    url = pathInfo.lstrip("/")

    # prompt to set url
    if url == "":
        print("Content-Type: text/html")
        print("")
        print("""
<html><body>
<form onsubmit="event.preventDefault();location.href='%s'+'/'+document.getElementById('url').value">
<label for="url">Set URL (for hierarchical reposotories, BASE/dists/DIST):</label><br>
<input type="text" name="url" id="url" size=100/>
<button type+"submit">Set</button>
</form></body></html>
""" % os.environ["SCRIPT_NAME"])
        return

    if "://" not in url and ":/" in url:
        url = url.replace(":/", "://")

    table = None
    # for flat repository, firstly try to get Packages

    rootURL = url
    idx = rootURL.find('/dists/')
    if idx > 0:
        rootURL = rootURL[:idx]

    if table is None:
        sourcesData = None
        resp = requests.get(url+"/Packages.xz")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(lzma.decompress(resp.content).decode("utf-8")).parse()
        resp = requests.get(url+"/Packages.bz2")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(bz2.decompress(resp.content).decode("utf-8")).parse()
        resp = requests.get(url+"/Packages.gz")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(gzip.decompress(resp.content).decode("utf-8")).parse()
        resp = requests.get(url+"/Packages")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(resp.text).parse()
        if sourcesData is not None:
            packageList2 = []
            for datum in sourcesData:
                dic = {e["tag"]:e["value"] for e in datum}
                fileURL = dic["Filename"]
                packageList2.append(
                    ('<a href="%s/%s">%s</a>' % (rootURL, fileURL, fileURL), dic["Size"],)
                )
            packageList2.sort()
            table = create_table(["Name", "Size"], packageList2)

    if table is None:
        sourcesData = None
        resp = requests.get(url+"/Sources.xz")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(lzma.decompress(resp.content).decode("utf-8")).parse()
        resp = requests.get(url+"/Sources.bz2")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(bz2.decompress(resp.content).decode("utf-8")).parse()
        resp = requests.get(url+"/Sources.gz")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(gzip.decompress(resp.content).decode("utf-8")).parse()
        resp = requests.get(url+"/Sources")
        if resp.status_code // 100 == 2:
            sourcesData = PackagesParser(resp.text).parse()
        if sourcesData is not None:
            packageList2 = []
            for datum in sourcesData:
                dic = {e["tag"]:e["value"] for e in datum}
                packageList = dic["Files"].split()
                i = 0
                while i < len(packageList):
                    fileURL = dic["Directory"]+"/"+packageList[i+2]
                    packageList2.append(
                        ('<a href="%s/%s">%s</a>' % (rootURL, fileURL, fileURL), packageList[i+1],)
                    )
                    i += 3
            packageList2.sort()
            table = create_table(["Name", "Size"], packageList2)

    if table is None:
        # then try to get Releases
        resp = requests.get(url+"/Release")
        if resp.status_code // 100 == 2:
            data = PackagesParser(resp.text).parse()
            dic = {e["tag"]:e["value"] for e in data[0]}
            if "MD5Sum" in dic:
                packageList = dic["MD5Sum"].split()
            elif "SHA1" in dic:
                packageList = dic["SHA1"].split()
            elif "SHA512" in dic:
                packageList = dic["SHA512"].split()
            else:
                print("Content-Type: text/plain")
                print("")
                print("Release file (%s) does not contain neither MD5Sum, SHA1 nor SHA512" % (url+"/Release",))
                exit()
            packageList = packageList[2::3]  # strip checksum and size fields
            packageList = [packages for packages in packageList if not os.path.basename(packages).startswith("Contents-")]
            packageList.sort()
            packageList = [os.path.dirname(packages) for packages in packageList]
            packageList2 = []
            for packages in packageList:
                if packages not in packageList2:
                   packageList2.append(packages)
            packageList2 = [
                ('<a href="%s/%s/%s">%s</a>' % (os.environ["SCRIPT_NAME"], url, packages, packages),)
                for packages in packageList2
            ]
            table = create_table(["PackageList"], packageList2)

    if table is None:
        print("Content-Type: text/plain")
        print("")
        print("Seems the url is not debian")
        return

    # template from https://qiita.com/developer-kikikaikai/items/f01599109ba1370a40d7
    html = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head><style>
table{
    border-collapse:collapse;
}
td,th{
    padding:10px;
    border-bottom:solid #ccc;
}
th{
    border-bottom:5px solid #ccc;
}
table tr th:nth-child(odd),
table tr td:nth-child(odd){
    background:#e6f2ff;
}
</style><body>
'''

    html += table
    html += "</body></html>"

    # HTTP header
    print("Content-Length: %d" % len(html))
    print("Content-Type: text/html")
    print("")
    # render html
    print(html)

if __name__ == "__main__":
    main()
