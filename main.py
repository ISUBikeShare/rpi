#!/usr/env/python
import json
import logging
import os
import serial
import struct
import sys
import time
import urllib2
import RPi.GPIO as GPIO
import uuid
from multiprocessing import Process, Queue

# DEBUG constant for verbose output
debug = True

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
        
        @param bike_id: the id of the bike to checkout
        @type bike_id: str
        @param rfid_id: the id of the user to checkout to
        @type rfid_id: str
        @return: if check-in was successful
        @rtype: boolean
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
        
        @param bike_id: the id of the bike to check into the dock
        @type bike_id: str
        @return: if check-in was successful
        @rtype: boolean
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


class Led(object):
    # step size for polling
    STEP = 0.25
    
    def __init__(self, gpio_id):
        """
        Initialize and start the LED thread on the given GPIO pin.
        
        @param gpio_id: the GPIO pin to run the LED on
        @type gpio_id: int
        """
        self.queue = Queue()
        self.gpio_id = gpio_id
        # setup the GPIO pin
        GPIO.setup(self.gpio_id, GPIO.OUT)
        GPIO.output(self.gpio_id, False)
        self.count = 0
        # start the event polling thread
        process = Process(target=self.poll_led)
        process.start()
        
    def poll_led(self):
        """
        Poll for events on this LED
        """
        print "LED started on GPIO pin %d" % self.gpio_id
        while True: # poll
            # every step, process all new durations
            while True:
                try:
                    duration = queue.get_nowait()
                    if duration > count or duration <= 0:
                        count = duration
                except EmptyException:
                    break;
        
            # if there is a positive duration, decrement the count by the step
            if count > 0:
                count -= Led.STEP
            # if the count is 0, turn off the led
            if count == 0:
                GPIO.output(self.gpio_id, False)
            # otherwise turn it on
            else
                GPIO.output(self.gpio_id, True)
            # sleep for step seconds
            time.sleep(Led.STEP)


class LedConnector(object):
    # GPIO pins
    GREEN = 6;
    YELLOW_1 = 13;
    YELLOW_2 = 19;
    RED = 26;

    def __init__(self):
        """
        Initialize the LED connector which provides an API for accessing the LEDs. LEDs run on separate threads.
        """
        self.queue = Queue()
        # setup GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        # add the leds
        self.leds = []
        self.leds.append((self.GREEN, Led(self.GREEN)))
        self.leds.append((self.YELLOW_1, Led(self.YELLOW_1)))
        self.leds.append((self.YELLOW_2, Led(self.YELLOW_2)))
        self.leds.append((self.RED, Led(self.RED)))
        # run the start-up display
        if not debug:
            self.startup_process = Process(target=self.startup)
            self.startup_process.start()
    
    def startup(self):
        """ 
        Startup animation 
        """
        self.trigger(self.GREEN, 4)
        time.sleep(1)
        self.trigger(self.YELLOW_1, 3)
        time.sleep(1)
        self.trigger(self.YELLOW_2, 2)
        time.sleep(1)
        self.trigger(self.RED, 1)

    def trigger(self, led_id, duration):
        """
        Trigger a given LED for duration. 
         - Positive durations trigger the LED for that ammount of time.
         - Negative durations turns on the LED
         - Zero duration turns off the LED
         
        @param led_id: the class variable which represents the LED to trigger an event on
        @type led_id: int
        @param duration: the integer duration in seconds to trigger the LED for
        @type duration: int
        """
        for id, led in self.leds if id == led_id:
            led.queue.put(duration)
            
    def reset(self):
        """ Reset all LEDs to off """
        for id, led in self.leds:
            led.queue.put(0)


class CardConnector(object):
    def __init__(self, queue):
        """
        Initialize the connection to the card reader.
        
        @param queue: the dock's main event queue
        @type queue: Queue
        """
        self.queue = queue
        self.ser = open('/dev/input/event0', 'r')

    def poll_card(self):
        """
        Poll for ISU card RFID events. The RFID reader reads from the HID 
        input event0 as a keyboard (/dev/input/event0).
        """
        key_data = []
        print "CardConnector started"
        while True:
            # read keyboard raw HID input and split into data pieces
            _, __, e_type, e_code, e_value = struct.unpack('LLHHl', self.ser.read(16))
            # check that the event is a key press
            if e_type == 1 and e_value:
                # get the pseudo-keycode
                key = e_code - 1
                # check that the key was an integer from 0-9
                if key in range(10):
                    key_data.append(key)
                # if the key was ENTER, push the event with the card id
                elif key == 27:
                    card_id = ''.join(str(x) for x in key_data)
                    print "Card event: %s" % card_id
                    self.queue.put((1, card_id))
                    key_data = []


class BikeConnector(object):
    def __init__(self, queue):
        """
        Initialize the connection to the bike id reader.
        
        @param queue: the dock's main event queue
        @type queue: Queue
        """
        self.queue = queue
        self.ser = serial.Serial('/dev/ttyUSB0')
        # self.ser = os.fdopen(os.pipe()[0], 'r', 0)

    def poll_bike(self):
        """
        Poll for bike NFC events. The NFC writes data to the first USB device (/dev/ttyUSB0).
        """
        print "BikeConnector started"
        while True:
            bike_id = self.ser.read(14)
            bike_id = bike_id.strip()
            print "Bike event: %s" % bike_id
            self.queue.put((2,bike_id))



class Dock(object):
    def __init__(self):
        """
        Initialize the dock and create connectors.
        """
        self.dock_id = uuid.getnode()
        print "Dock ID: %s" % repr(self.dock_id)
        self.server = ServerConnector(self.dock_id)
        # TODO: Need to initialize with current bike ******************************
        self.bike_id = 1
        self.queue = Queue()
        self.card_connector = CardConnector(self.queue)
        self.bike_connector = BikeConnector(self.queue)
        self.led_connector = LedConnector()

    def start(self):
        """
        Start the main dock thread which polls for and handles Card and Bike events.
        """
        # create and start event processes
        card_proc = Process(target=self.card_connector.poll_card)
        card_proc.start()
        bike_proc = Process(target=self.bike_connector.poll_bike)
        bike_proc.start()

        # poll events queue and handle events
        print "Dock Started! Now polling for events..."
        while True:
            sender, data = self.queue.get()
            if sender == 1:
                # message from CardConnector
                if self.bike_id is not None:
                    if self.server.check_out(self.bike_id, data):
                        # dispatch bike to user
                        print "Bike with id (%s) successfully checked out" % self.bike_id
                        self.led_connector.trigger(LedConnector.GREEN, 4)
                        self.bike_id = None
                    else:
                        # display error to user
                        print "Bike checkout failed"
                        self.led_connector.trigger(LedConnector.RED, 4)
                else:
                    # display error to user
                    print "No bike in dock"
                    self.led_connector.trigger(LedConnector.RED, 4)

            elif sender == 2:
                # message from BikeConnector
                if self.bike_id is None:
                    if self.server.check_in(1):
                        # successful check in
                        self.bike_id = 1
                        print "Bike with id (%s) successfully checked in" % self.bike_id
                        self.led_connector.trigger(LedConnector.GREEN, 4)
                    else:
                        # display error to user
                        print "Bike check-in failed"
                        self.led_connector.trigger(LedConnector.RED, 4)
                else:
                    # display error to user
                    print "There is already a bike in the dock"
                    self.led_connector.trigger(LedConnector.RED, 4)


def main():
    """
    Create the dock object with the MAC address as the dock id.
    """
    print "=== CyShare Dock Firmware ==="
    
    dock = Dock(dock_id)
    dock.start()


if __name__ == '__main__':
    """
    Entry point for python application.
    """
    main()
