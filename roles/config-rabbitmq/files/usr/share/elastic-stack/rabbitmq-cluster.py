#!/usr/bin/env python
# coding=utf-8
# besme allah
# author ali.ahmadi
# 1400-12-06

import os
import sys
import socket
import datetime
import time
import threading
from time import sleep
import argparse
from subprocess import PIPE, Popen

# from psutil import process_iter
# from signal import SIGTERM # or SIGKILL

# rabbitmq nodes
node_list = [
    {"name": "rabbit", "port": 5672, "config_file": "/etc/rabbitmq/rabbitmq.conf"},
    {"name": "rabbit_1", "port": 5673, "config_file": "/etc/rabbitmq/rabbitmq_1.conf"},
    {"name": "rabbit_2", "port": 5674, "config_file": "/etc/rabbitmq/rabbitmq_2.conf"},
]

# you dont need to modify next variables
parser = argparse.ArgumentParser()
parser.add_argument('-a', "--action", help="request action type ",
                    choices=['deploy', 'start', 'stop', 'restart', 'health'],
                    required=True)
parser.add_argument('-v', "--verbose", help="show logs", choices=['0', '1'], default=0)
parser.add_argument('-n', "--node", help="node name", choices=['all', 'rabbit', 'rabbit_1', 'rabbit_2'], default='all')
parser.add_argument('-s', "--service", help="run as service", choices=['0', '1'], default=0)
args = parser.parse_args()


def myLogger(log_type, message, force_verbose=False):
    log_path = "/var/log/rabbitmq-cluster.log"
    log_date_time = datetime.datetime.fromtimestamp(time.time())
    log_message = '{"datetime":"%s", "type":"%s", "log":"%s"} \n ' % (log_date_time, log_type, message)
    try:
        with open(log_path, "a+") as out:
            out.write(log_message + "\n")
            out.close()
        if str(args.verbose) == '1' or force_verbose:
            print(log_message)
    except Exception as ex:
        print(ex)


def getProcessSocketLock():
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Create an abstract socket, by prefixing it with null.
        s.bind('\0postconnect_gateway_notify_lock')
        # return True
    except socket.error as e:
        error_code = e.args[0]
        error_string = e.args[1]
        message = "Another rabbitmq-cluster.py already running (%d:%s ). Exiting" % (error_code, error_string)
        myLogger("ERROR", message, True)
        # return False
        sys.exit(0)


def cmdLine(command):
    try:
        myLogger("INFO", "executing command '%s'" % command)
        # os.system(command)
        process = Popen(
            args=command,
            stdout=PIPE,
            shell=True
        )
        return process.communicate()[0]
    except Exception as ex:
        myLogger("ERROR", str(ex))


def cmdLineAsThread(command):
    t = threading.Thread(target=cmdLine, args=(command,))
    t.daemon = True
    t.start()


def portIsOpen(port):
    try:
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        location = ("127.0.0.1", port)
        result_of_check = a_socket.connect_ex(location)
        a_socket.close()
        if result_of_check == 0:
            myLogger("INFO", "port %s is open " % port)
            return True
        else:
            myLogger("INFO", "port %s is not open " % port)
            return False
    except Exception as ex:
        myLogger("ERROR", str(ex))
    return False


def killProcessByPort(port):
    try:
        myLogger("INFO", "kill process that use port %s " % port)
        cmdLine('kill -9 $(lsof -t -i:%s)' % port)
        sleep(10)
        # for proc in process_iter():
        #     for conns in proc.connections(kind='inet'):
        #         if conns.laddr.port == port:
        #             proc.send_signal(SIGTERM)  # or SIGKILL
    except Exception as ex:
        myLogger("ERROR", str(ex))


def stopApp(name, port):
    if name == 'rabbit':
        cmdLine('systemctl stop rabbitmq-server.service')
    else:
        # if args.action == 'deploy':
        cmdLineAsThread('rabbitmqctl --node %s stop_app ' % name)

        l = 0
        while l < 10 and portIsOpen(port):
            l = l + 1
            myLogger("INFO", "waiting 5s(%s of 10) for stopping node %s" % (l, name))
            sleep(5)
        if portIsOpen(port):
            killProcessByPort(port)


def resetApp(name):
    if name == 'rabbit':
        pass
    else:
        cmdLine('rabbitmqctl --node %s reset ' % name)


def joinCluster(name):
    if name == 'rabbit':
        pass
    else:
        cmdLine('rabbitmqctl --node %s join_cluster rabbit' % name)


def startApp(name, port):
    try:
        if portIsOpen(port):
            myLogger("INFO", "port %s is open and dont need to start_app %s" % (port, name))
        else:
            if name == 'rabbit':
                command = 'systemctl start rabbitmq-server.service'
            else:
                command = 'rabbitmqctl --node %s start_app' % name
            sleep(3)
            cmdLineAsThread(command)
            sleep(20)
            l = 0
            while l < 20 and not portIsOpen(port):
                l = l + 1
                myLogger("INFO", "monitoring 5s(%s of 20) for start node %s" % (l, name))
                sleep(5)
            if not portIsOpen(port):
                myLogger("ERROR", "can not start node %s" % name)
    except Exception as ex:
        myLogger("ERROR", str(ex))


def addNewNode(name, port, config_file):
    if name != 'rabbit':
        if portIsOpen(port):
            myLogger("INFO", "port %s is open and dont need to add new node %s" % (port, name))
        else:
            if portIsOpen(20000 + port):
                killProcessByPort(20000 + port)

            cmdLineAsThread(
                'RABBITMQ_NODE_PORT=%s RABBITMQ_CONFIG_FILE="%s" RABBITMQ_NODENAME="%s" rabbitmq-server &' % (
                    port, config_file, name))

            l = 0
            while l < 20 and not portIsOpen(port):
                l = l + 1
                myLogger("INFO", "waiting 5s(%s of 20) for add new node %s" % (l, name))
                sleep(5)
            sleep(10)


def doAction(node, node_number):
    sleep(node_number * 45)
    if args.action == "deploy":
        if node["name"] == 'rabbit':
            startApp(node["name"], node["port"])
        else:
            addNewNode(node["name"], node["port"], node["config_file"])
            stopApp(node["name"], node["port"])
            resetApp(node["name"])
            joinCluster(node["name"])
            startApp(node["name"], node["port"])

    elif args.action == "stop":
        if str(args.service) == '1' and node["name"] == 'rabbit':
            myLogger("WARNING", "ignore stopping node rabbit by 'systemctl stop rabbitmq-cluster.service'."
                                " you can run 'systemctl stop rabbitmq-server.service' manually.")
        else:
            stopApp(node["name"], node["port"])

    elif args.action == "start":
        # Sometimes you need to run addNewNode after rebooting the device and startApp do not work alone
        addNewNode(node["name"], node["port"], node["config_file"])
        startApp(node["name"], node["port"])

    elif args.action == "health":
        if not portIsOpen(node["port"]):
            # Sometimes you need to run addNewNode after rebooting the device and startApp do not work alone
            addNewNode(node["name"], node["port"], node["config_file"])
            startApp(node["name"], node["port"])

    elif args.action == "restart":
        stopApp(node["name"], node["port"])
        sleep(10)
        # Sometimes you need to run addNewNode after rebooting the device and startApp do not work alone
        addNewNode(node["name"], node["port"], node["config_file"])
        startApp(node["name"], node["port"])


def mainProcess():
    myLogger("INFO", "process started, action:%s, nodes:%s" % (args.action, args.node))
    threads = list()
    i = 0
    node_ports = []
    for ds in node_list:
        node_ports.append(ds["port"])
        if args.node == "all" or args.node == ds["name"]:
            x = threading.Thread(target=doAction, args=(ds, i,))
            i = i + 1
            threads.append(x)
            x.start()

    for x in threads:
        x.join()

    ports_status = ""
    for np in node_ports:
        ports_status = ports_status + "%s:%s ," % (np, portIsOpen(np))
    myLogger("INFO",
             "process ended, action:%s, nodes:%s, final port status %s " % (args.action, args.node, ports_status))


if __name__ == "__main__":
    mainProcess()
    if str(args.service) == '1' and (args.action == "start" or args.action == "restart"):
        args.action = 'check'
        while True:
            myLogger("INFO", "The health of the cluster nodes will be checked again in the next 3600 seconds.")
            sleep(3600)
            mainProcess()
    sys.exit(0)
