#!/usr/env/python
import json
import logging
import urllib2
import uuid
import serial


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
        self.ser = serial.Serial('/dev/ttyUSB0')

    def poll_bike(self):
        s = self.ser.read(16)
        s = s[:-2]
        self.queue.put([2,s])


class CardConnector(object):
    def __init__(self, queue):
        self.queue = queue

    def poll_card(self):
        while True:
            card_id = raw_input('> ')
            self.queue.put([1, card_id])


class Dock(object):
    def __init__(self, server, bike_connector):
        self.server = server
        self.bike = bike_connector

    def poll_card(self):
        """
        Poll STDIN for card read signals.
        """
        while True:
            card_id = raw_input('> ')
            success = self.server.check_out(self.bike.id, card_id)
            if success:
                # Release lock
                print("success")
            else:
                # Invalid request, error user
                print("failure")
 

def main():
    """
    Start rfid and card threads. Configure dock on first run.
    """
    dock_id = initialize_dock()
    server_connector = ServerConnector(dock_id)
    bike_connector = BikeConnector(bike_id=1)
    dock = Dock(server_connector, bike_connector)
    dock.poll_card()


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
