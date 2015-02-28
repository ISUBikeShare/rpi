#!/usr/env/python
import urllib2
import json


class ServerConnector(object):
    def __init__(self, dock_id):
        """
        Initialize connection with server.

        @param dock_id: the MAC address of this dock_id
        @type dock_id: str
        """
        self.dock_id = dock_id

    def check_out(self, bike_id, rfid_id):
        """
        Send request to server requesting a user checkout.
        """
        pass

    def check_in(self, bike_id):
        """
        Send request signifying bike check in.
        """
        pass

    def _make_request(self, data):
        """
        Send data to server and return response in json
        """
        pass

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