#!/usr/env/python
import json
import logging
import os
import serial
import string
import struct
import sys
import json
import time
import urllib2
import RPi.GPIO as GPIO
import uuid
import os.path
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
        try:
            resp = self._make_request('checkout', data)
        except Exception as e:
            return False

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
        try:
            resp = self._make_request('checkin', data)
        except Exception as e:
            return False

        if resp.code == 200:
            return True
        return False

    def register_dock(self, dock_id):
        """
        Send request signifying bike check in.
        """
        data = {
            'dockID': dock_id,
        }
        try:
            resp = self._make_request('dock', data)
        except Exception as e:
            return False

        if resp.code == 200 or resp.code == 204:
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
        print data
        ret = urllib2.urlopen(req)
        print 'returned'
        return ret


class BikeConnector(object):
    def __init__(self, queue):
        self.queue = queue
        self.ser = serial.Serial('/dev/ttyUSB0')

    def poll_bike(self):
        print "BikeConnector started"
        while True:
            bike_id = self.ser.readline()
            bike_id = ''.join(
                c for c in bike_id if c in string.printable).strip()
            print "read bike_id %s" % bike_id
            self.queue.put((2,bike_id))




class LockConnector(object):
    def __init__(self):
        print "LockConnector started"
        self.pin_num = 21
        self.queue = Queue()
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin_num, GPIO.OUT)
        GPIO.output(self.pin_num, False)

    def trigger(self):
        GPIO.output(self.pin_num, True)
        time.sleep(1);
        GPIO.output(self.pin_num, False)


class LedConnector(object):
    RED = 13;
    GREEN = 19;
    BLUE = 26;
    WHITE = 0;

    def __init__(self):
        print "LedConnector started"
        self.queue = Queue()
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RED, GPIO.OUT)
        GPIO.setup(self.BLUE, GPIO.OUT)
        GPIO.setup(self.GREEN, GPIO.OUT)
        GPIO.output(self.RED, False)
        GPIO.output(self.BLUE, False)
        GPIO.output(self.GREEN, False)


    def poll_led(self):
        while True:
            led_id, status = self.queue.get()
            self.set_color(led_id)
            print "setting color to ", led_id
            time.sleep(3)
            if status:
                self.set_color(self.WHITE)
                print "setting color to white"
            else:
                self.set_color(self.BLUE)
                print "setting color to blue"

    def trigger(self, led_id, status):
        self.queue.put((led_id, status))

    def set_color(self, color):
        if color == self.RED:
            GPIO.output(self.BLUE, False)
            GPIO.output(self.GREEN, False)
            GPIO.output(self.RED, True)
        elif color == self.BLUE:
            GPIO.output(self.BLUE, True)
            GPIO.output(self.GREEN, False)
            GPIO.output(self.RED, False)
        elif color == self.GREEN:
            GPIO.output(self.BLUE, False)
            GPIO.output(self.GREEN, True)
            GPIO.output(self.RED, False)
        else:
            GPIO.output(self.BLUE, True)
            GPIO.output(self.GREEN, True)
            GPIO.output(self.RED, True)

class CardConnector(object):
    def __init__(self, queue):
        self.queue = queue
        self.ser = open('/dev/input/event0', 'r')

    def poll_card(self):
        key_data = []
        print "CardConnector started"
        while True:
            _, __, e_type, e_code, e_value = struct.unpack('LLHHl', self.ser.read(16)) 
            if e_type == 1 and e_value:
                key = e_code - 1
                if key in range(10):
                    key_data.append(key)
                elif key == 27:
                    card_id = ''.join(str(x) for x in key_data)
                    print "read card_id %s" % card_id
                    self.queue.put((1, card_id))
                    key_data = []


class Dock(object):
    def __init__(self, dock_id, bike_id=None):
        if os.path.isfile('./dock_state'):
            with open('dock_state') as data_file:    
                json_data = json.load(data_file)
                self.bike_id = json_data["bike_id"]
        else:
            self.bike_id = None


        self.server = ServerConnector(dock_id)
        if not self.server.register_dock(dock_id):
            print "dock not registered"
        self.queue = Queue()
        self.card_connector = CardConnector(self.queue)
        self.bike_connector = BikeConnector(self.queue)
        self.led_connector = LedConnector()
        self.lock_connector = LockConnector()

        if self.bike_id:
            self.led_connector.set_color(self.led_connector.WHITE)
        else:
            self.led_connector.set_color(self.led_connector.BLUE)

    def start(self):
        card_proc = Process(target=self.card_connector.poll_card)
        bike_proc = Process(target=self.bike_connector.poll_bike)
        led_proc = Process(target=self.led_connector.poll_led)

        card_proc.start()
        bike_proc.start()
        led_proc.start()

        while True:
            sender, data = self.queue.get()
            if sender == 1:
                # Message from CardConnector
                if self.bike_id is not None:
                    if self.server.check_out(self.bike_id, data):
                        # dispatch bike to user
                        self.bike_id = None
                        self.led_connector.trigger(LedConnector.GREEN, self.bike_id)
                        self.lock_connector.trigger()
                        print "bike checked out", self.bike_id
                        json_data = {'bike_id': self.bike_id}
                        with open('dock_state', 'w') as outfile:
                            outfile.write(json.dumps(json_data))
                    else:
                        # Display error to user
                        self.led_connector.trigger(LedConnector.RED, self.bike_id)
                        print "bike checkout failed"
                else:
                    # Display error to user
                    print "bike is None"
                    self.led_connector.trigger(LedConnector.RED, self.bike_id)

            elif sender == 2:
                # Message from BikeConnector
                if self.bike_id is None:
                    if self.server.check_in(data):
                        # successful check in
                        self.bike_id = data
                        self.led_connector.trigger(LedConnector.GREEN, self.bike_id)
                        print "bike checked in", self.bike_id
                        json_data = {'bike_id': self.bike_id}
                        with open('dock_state', 'w') as outfile:
                            outfile.write(json.dumps(json_data))
                    else:
                        # Display error to user
                        self.led_connector.trigger(LedConnector.RED, self.bike_id)
                        print "bike check in failed"
                else:
                    # Display error to user
                    self.led_connector.trigger(LedConnector.RED, self.bike_id)
                    print "bike is not None"


def main():
    """
    Start rfid and card threads. Configure dock on first run.
    """
    dock_id = initialize_dock()

    # Need to initialize with current bike
    dock = Dock(dock_id, bike_id="6A004A1589BC")
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
