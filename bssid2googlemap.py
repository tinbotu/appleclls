#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 sts=4 ff=unix ft=python expandtab

import getopt
import requests
import re
import sys
import urllib

import clls_pb2


def usage(me='me'):
    print("usage: %s -vnm [OPTIONS] target_essid [target_essid] [target_essid] ...\n"
          "[OPTIONS]\n"
          " -v --verbose\n"
          " -n --neighbour\n"
          " -m --machine-readable\n"
          "e.g. %s -n 00:11:22:de:ad:bf"
          % (me, me))


def query_cllswloc(query_bssid, neighbour=False):
    query = clls_pb2.cllswloc()
    q = query.ap.add()
    q.bssid = query_bssid
    query.get_neighbour = 0 if neighbour else 1

    query_serialized = query.SerializeToString()

    # padding apple's nazo binary, not pb, at head
    data = ("\x00\x01\x00\x05en_US\x00\x13com.apple.locationd\x00\x0c8.1.2.12B440\x00\x00\x00\x01\x00\x00\x00%c%s" % (len(query_serialized), query_serialized))

    headers = {'Accept': '*/*',
               'Accept-Encoding': 'gzip, deflate',
               'Content-Type': 'application/x-www-form-urlencoded',
               'User-Agent': 'locationd/1861.0.23 CFNetwork/758.2.8 Darwin/15.0.0',
               'Accept-Language': 'en-us', }

    r = requests.post('https://gs-loc.apple.com/clls/wloc', headers=headers, data=data, verify=False, timeout=10)

    if not r.status_code == requests.codes.ok:
        raise

    loc = clls_pb2.cllswloc()
    loc.ParseFromString(r.content[10:])  # skip nazo header 10bytes
    return loc


def reformat_mac(mac):
    m = re.split(r'[:\-\.]', mac)
    if len(m) == 6:
        mac = ':'.join([hex(int(m[i], base=16))[2:] for i in range(6)])
    elif len(m) == 1:
        mac = ':'.join(["%s" % (mac[i:i+2]) for i in range(0, 12, 2)])

    return mac


def get_one_bssidlocation(bssid):
    try:
        response = query_cllswloc(reformat_mac(bssid), neighbour=False)
    except requests.exceptions.Timeout:
        return (None, None)

    lat = response.ap[0].location.latitude / 1e8
    lng = response.ap[0].location.longitude / 1e8
    if lng == -180.:
        return (None, None)
    else:
        return (lat, lng)


def show_bssidlocation(bssids, neighbour=False, machine_readable=False, verbose=None):

    if bssids is None or bssids == []:
        usage(me=sys.argv[0])
        return

    for bssid in bssids:

        try:
            response = query_cllswloc(reformat_mac(bssid), neighbour=neighbour)
        except requests.exceptions.Timeout:
            continue

        if len(response.ap) == 0 and machine_readable:
            print("0\t0\t%s" % (bssid))
            return

        for ap in response.ap:
            lat = ap.location.latitude / 1e8
            lng = ap.location.longitude / 1e8

            if lng == -180.:
                if machine_readable:
                    print("0\t0\t%s" % (ap.bssid))

                if verbose:
                    print("Not found or you banned temporary")
                continue

            if not machine_readable:
                print("http://maps.google.com/?ll=%f,%f&q=%f,%f%%28%s%%29" % (lat, lng, lat, lng, urllib.quote(ap.bssid)))
            else:
                print("%f\t%f\t%s" % (lat, lng, ap.bssid))

            # sometimes multiple response come even neighbour flag is not true
            if not neighbour:
                break



def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "vhnm", ["verbose", "help", "neighbour", "machine-readable"])
    except getopt.GetoptError:
        usage(me=sys.argv[0])
        sys.exit(1)

    verbose = 0
    neighbour = False
    machine_readable = False

    for o, a in opts:
        if o == "-v":
            verbose = 1
        elif o in ("-h", "--help"):
            usage(me=sys.argv[0])
            sys.exit(0)
        elif o in ("-n", "--neighbour"):
            neighbour = True
        elif o in ("-m", "--machine-readable"):
            machine_readable = True
        else:
            assert False, "unknown option"

    show_bssidlocation(args, neighbour=neighbour, machine_readable=machine_readable, verbose=verbose)



if __name__ == "__main__":
    main()
