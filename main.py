#!/usr/env/python
import json
import logging
import os
import serial
import sys
import urllib2
import uuid
from multiprocessing import Process, Queue


class ServerConnector(object):
    def __init__(self, dock_id, url=None):
        """
        Initialize connection with server.

        @param dock_id: the MAC address of this dock_id
        @type dock_id: str
        """
        self.base_url = url or 'https://secure-brook-1414.herokuapp.com/api/%s'
        self.dock_id = dock_id

    def check_out(self, bike_id, rfid_id):
        """
        Send request to server requesting a user checkout.
        """
        data = {
            'bikeID': bike_id,
            'cardString': rfid_id
        }
        resp = self._make_request('checkout', data)
        if resp.code == 200:
            return True
        return False


    def check_in(self, bike_id):
        """
        Send request signifying bike check in.
        """
        data = {
            'bikeID': bike_id,
        }
        resp = self._make_request('checkin', data)
        if resp.code == 200:
            return True
        return False

    def _make_request(self, endpoint, data):
        """
        Send data to server and return response in json
        """
        data.update({'dockID': self.dock_id})
        url = self.base_url % endpoint
        headers = {'Content-Type': 'application/json'}
        req = urllib2.Request(url, data=json.dumps(data), headers=headers)
        print('Opening URL: ' + url)
        return urllib2.urlopen(req)


class BikeConnector(object):
    def __init__(self, queue):
        self.queue = queue
        # self.ser = serial.Serial('/dev/tty0')
        self.ser = os.fdopen(os.pipe()[0], 'r', 0)

    def poll_bike(self):
        print "BikeConnector started"
        while True:
            bike_id = self.ser.read(16)
            bike_id = bike_id.strip()
            print "read bike_id %s" % bike_id
            self.queue.put((2,bike_id))


class CardConnector(object):
    def __init__(self, queue):
        self.queue = queue
        self.stream = os.fdopen(0, 'r', 0)

    def poll_card(self):
        print "CardConnector started"
        while True:
            card_id = self.stream.read(6)
            print "read card_id %s" % card_id
            self.queue.put((1, card_id))


class Dock(object):
    def __init__(self, dock_id, bike_id=None):
        self.server = ServerConnector(dock_id)
        self.bike_id = bike_id
        self.queue = Queue()
        self.card_connector = CardConnector(self.queue)
        self.bike_connector = BikeConnector(self.queue)

    def start(self):
        card_proc = Process(target=self.card_connector.poll_card)
        bike_proc = Process(target=self.bike_connector.poll_bike)

        card_proc.start()
        bike_proc.start()

        while True:
            sender, data = self.queue.get()
            if sender == 1:
                # Message from CardConnector
                if self.bike_id is not None:
                    if self.server.check_out(self.bike_id, data):
                        # dispatch bike to user
                        pass
                    else:
                        # Display error to user
                        pass
                else:
                    # Display error to user
                    pass

            elif sender == 2:
                # Message from BikeConnector
                if self.bike_id is None:
                    if self.server.check_in(data):
                        # successful check in
                        self.bike_id = data
                    else:
                        # Display error to user
                        pass
                else:
                    # Display error to user
                    pass


def main():
    """
    Start rfid and card threads. Configure dock on first run.
    """
    dock_id = initialize_dock()

    # Need to initialize with current bike
    dock = Dock(dock_id, 1)
    dock.start()


def initialize_dock():
    """
    On startup, sends dock status and identifier to server.

    @return: MAC address (dock id) of this dock
    @rtype: str
    """
    # register dock via MAC
    return uuid.getnode()


if __name__ == '__main__':
    """
    Entry point for python application.
    """
    main()
