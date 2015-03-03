#!/usr/env/python
import json
import logging
import urllib2


class ServerConnector(object):
    def __init__(self, dock_id, url=None):
        """
        Initialize connection with server.

        @param dock_id: the MAC address of this dock_id
        @type dock_id: str
        """
        self.base_url = url or 'http://127.0.0.1:8080/api/%s'
        self.dock_id = dock_id

    def check_out(self, bike_id, rfid_id):
        """
        Send request to server requesting a user checkout.
        """
        data = {
            'bikeID': bike_id,
            'cardID': rfid_id
        }
        resp = self._make_request('checkout', data)
        if resp.status == 200:
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
        if resp.status == 200:
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
    def __init__(self, server, bike_id=None):
        self.server = server
        self.bike_id = bike_id

    def poll_bike(self):
        """
        Poll RFID reader for bike check in.
        """
        pass


class CardConnector(object):
    def __init__(self, server):
        self.server = server

    def poll_card(self):
        """
        Poll STDIN for card read signals.
        """
        pass

class DebugServer(object):
    def __init__(self):
        pass


def main():
    """
    Start rfid and card threads. Configure dock on first run.
    """
    dock_id = initialize_dock()
    server_connector = ServerConnector(dock_id)
    bike_connector = BikeConnector()
    card_connector = CardConnector()


def initialize_dock():
    """
    On startup, sends dock status and identifier to server.

    @return: MAC address (dock id) of this dock
    @rtype: str
    """
    # register dock via MAC
    pass


if __name__ == '__main__':
    """
    Entry point for python application.
    """
    main()
