#!/usr/bin/env python
# coding=utf-8
# besme allah
# author ali.ahmadi
# 1400-11-29

from ast import Try
import os
import sys
import socket
import datetime
import time
import threading
from time import sleep
import argparse

# datasources that you want to send
datasource_list = [
    {"name":"zeek conn", "eps": 280, "to_file": True, "to_port": True , "destination_port": None, "source_file": "./zeek-logs/conn.log" , "destination_file": "/opt/zeek/logs/current/conn.log" },
    {"name":"zeek dns ", "eps": 29, "to_file": True, "to_port": True , "destination_port": None, "source_file": "./zeek-logs/dns.log" , "destination_file": "/opt/zeek/logs/current/dns.log" },
    {"name":"zeek dhcp", "eps": 1, "to_file": True, "to_port": True , "destination_port": None, "source_file": "./zeek-logs/dhcp.log" , "destination_file": "/opt/zeek/logs/current/dhcp.log" },
    {"name":"zeek http", "eps": 190, "to_file": True, "to_port": True , "destination_port": None, "source_file": "./zeek-logs/http.log" , "destination_file": "/opt/zeek/logs/current/http.log" },
    {"name":"zeek ssl ", "eps": 14, "to_file": True, "to_port": True , "destination_port": None, "source_file": "./zeek-logs/ssl.log" , "destination_file": "/opt/zeek/logs/current/ssl.log" },
    {"name":"zeek x509", "eps": 2, "to_file": True, "to_port": True , "destination_port": None, "source_file": "./zeek-logs/x509.log" , "destination_file": "/opt/zeek/logs/current/x509.log" },
    {"name":"zeek ssh", "eps": 2, "to_file": True, "to_port": True , "destination_port": None, "source_file": "./zeek-logs/ssh.log" , "destination_file": "/opt/zeek/logs/current/ssh.log" },
    {"name":"fortigate", "eps": 5, "to_file": True, "to_port": True , "destination_port": 5141, "source_file": "./fortigate.log" , "destination_file": None },

]

# for execute file use this commands:
# cd /file_location
# python3 ./generate_test_events

# you can change eps ratio to 2*eps, and maximum event count to 500000 event like this command:
# python3 ./generate_test_events -r2 -t500000

# you dont need to modify next variables
parser = argparse.ArgumentParser()
parser.add_argument('-r', "--ratio", help="to send events by higher EPS default 1", type=int, default=1)
parser.add_argument('-t', "--total", help="maximum event count default 1000000", type=int, default=1000000)
parser.add_argument('-i', "--interval", help="logging interval in seconds default 5", type=int, default=5)
parser.add_argument('-H', "--host", help="remote syslog server ip.", default="localhost")
args = parser.parse_args()


FACILITY = {
    'kern': 0, 'user': 1, 'mail': 2, 'daemon': 3,
    'auth': 4, 'syslog': 5, 'lpr': 6, 'news': 7,
    'uucp': 8, 'cron': 9, 'authpriv': 10, 'ftp': 11,
    'local0': 16, 'local1': 17, 'local2': 18, 'local3': 19,
    'local4': 20, 'local5': 21, 'local6': 22, 'local7': 23,
}

LEVEL = {
    'emerg': 0, 'alert':1, 'crit': 2, 'err': 3,
    'warning': 4, 'notice': 5, 'info': 6, 'debug': 7
}

def syslog(message,host='localhost', port=514, level=LEVEL['notice'], facility=FACILITY['daemon']):
    """
    Send syslog UDP packet to given host and port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = '<%d>%s' % (level + facility*8, message)
    sock.sendto(data.encode('utf-8'), (host, port))
    sock.close()

output_event_count = 0
output_event_status = {};

def sendEvent(event,to_port,destination_port,to_file,destination_file):
    global output_event_count

    if to_port and destination_port != None:
        syslog(event,args.host, destination_port)
    if to_file and destination_file != None:
        with open(destination_file, "a+") as out:
            out.write(event + "\n")
            out.close()
    output_event_count = output_event_count + 1


def readEvent(ds):
    global output_event_status
    try:
        if ds["source_file"] == None:
            print("there is no available source file for datasource: %s" %(ds["name"]))
            return
        if not ((ds["to_port"] and ds["destination_port"] != None ) or (ds["to_file"] and ds["destination_file"] != None)):
            print("there is no available output for datasource: %s" %(ds["name"]))
            return
        send_count_total = 0
        send_count_this_second = 0
        start_time = datetime.datetime.now()
        try:
            os.system("rm -rf " + ds["destination_file"])
        except Exception as ex:
            pass

        while True:
            with open(ds["source_file"], "r+") as source_file:
                reader = source_file.read()
                for i, event in enumerate(reader.split("\n")):
                    if output_event_count >= args.total:
                        return
                    sendEvent(event,ds["to_port"],ds["destination_port"],ds["to_file"],ds["destination_file"])
                    send_count_total = send_count_total + 1
                    send_count_this_second = send_count_this_second + 1
                    end_time = datetime.datetime.now()
                    time_diff = (end_time - start_time) * 1
                    execution_time = time_diff.total_seconds()
                    if execution_time >= 1 or send_count_this_second >= ds["eps"]:
                        output_event_status[ds["name"]] = "%s eps, %s total" %( send_count_this_second , send_count_total)
                        if execution_time < 1:
                            sleep( abs (1.0 - execution_time) )
                        send_count_this_second = 0
                        start_time = datetime.datetime.now()
    except Exception as ex:
        print(ex)



if __name__ == "__main__":
    threads = list()
    for ds in datasource_list:
        ds["eps"] = ds["eps"] * args.ratio
        x = threading.Thread(target=readEvent, args=(ds,))
        threads.append(x)
        x.start()

    tmp_output_event_count = 0
    while output_event_count < args.total:
        sleep(args.interval)
        eps = (output_event_count - tmp_output_event_count) / args.interval
        print ("%s total event count:%s, latest EPS for %s seconds :%s, detail: %s \n" % (datetime.datetime.fromtimestamp(time.time()), output_event_count,args.interval,eps, output_event_status) )
        tmp_output_event_count = output_event_count

    print ("%s process exit, total events:%s" % (datetime.datetime.fromtimestamp(time.time()), output_event_count) )
    sys.exit(0)

