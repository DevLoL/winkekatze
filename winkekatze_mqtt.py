#!/usr/bin/python3

###
# Copyright 2015, Aurel Wildfellner.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import time
import serial
import argparse

import mosquitto
import topicconfig
from topictypes import TopicTypes



class WinkekatzeConnection:

    def __init__(self):
        self._serial = None
        self.isConnected = False


    def connect(self, device, baudrate):
        if self.isConnected:
            return True

        try:
            self._serial = serial.Serial(device, baudrate)
        except:
            return False
        # update open and locked info
        self.isConnected = self._serial.isOpen()
        return self.isConnected


    def wink(self):
        print("Wink")
        self._sendCommand("WINK;")

    def wink3(self):
        print("Wink 3")
        self._sendCommand("WINK3;")

    def reset(self):
        print("Reset")
        self._send_Command("RESET;")


    def _sendCommand(self, cmd):
        """ Sends a command string to the arduino. """
        if self._serial and self._serial.isOpen():
            try:
                self._serial.write(bytearray(cmd, "ASCII"))
                print("printed to serial:", cmd)
            except:
                self.isConnected = False;
        else:
            self.isConnected = False;




class MQTT_TOPICS:
    winkekatze = "pusteblume/winkekatze"
    winkekatze = "devlol/winkekatze"
    hi5 = "devlol/h19/mainroom/craftui/button/buttonHi5"



def on_message(client, winkekatze, msg):
    payload = msg.payload.decode("utf-8")
    print(payload)
    """ Callback for mqtt message."""
    for ctopic in topicconfig.cat_topics:
        
        if ctopic['topic'] == msg.topic:
            
            if ctopic['type'] == TopicTypes.WINKEKATZE:
                if payload == "WINK":
                    winkekatze.wink()
                elif payload == "WINK3":
                    winkekatze.wink3()
                elif payload == "RESET":
                    winkekatze.reset()
                elif "CMD:" in payload: # send a raw command to the cat
                    cmd = payload[4:].strip() + ";"
                    print(cmd)
                    winkekatze._sendCommand(cmd)
            
            elif ctopic['type'] == TopicTypes.TRIGGER_ON_PAYLOAD:
                if ctopic['payload'] == payload:
                    winkekatze._sendCommand(ctopic['command'])

            elif ctopic['type'] == TopicTypes.TRIGGER_ON_POST:
                winkekatze._sendCommand(ctopic['command'])


def on_disconnect(client, userdata, foo):
    connected = False
    while not connected:
        try:
            client.reconnect()
            connected = True
            # resubscribe to the topics
            for ctopic in topicconfig.cat_topics:
                client.subscribe(ctopic['topic'])
        except:
            print("Failed to reconnect...")
            time.sleep(1)


def tryToConnectArduino(winkekatze, devname="ttyACM", num=10):
    devices =  ["/dev/" + devname + str(x) for x in range(num)]

    for device in devices:
        winkekatze.connect(device, 9600)
        if winkekatze.isConnected:
            break


def main():

    ## Command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("-d")

    args = parser.parse_args() 
    devicePath = args.d
    gotDevicePath = (devicePath != None)
    brokerHost = args.host
    
    ## setup MQTT client
    client = mosquitto.Mosquitto()
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(brokerHost)
    except:
        print("failed to connect")
        on_disconnect(client, None, None)

    ## subscribe to topics
    for ctopic in topicconfig.cat_topics:
        client.subscribe(ctopic['topic'])

    ## winkekatze
    winkeKatze = WinkekatzeConnection()
    print("Connecting to Arduino.... ", end="")
    if (gotDevicePath):
        winkeKatze.connect(devicePath, 9600)
    else:
        tryToConnectArduino(winkeKatze)
    if winkeKatze.isConnected:
        print("done.")
    else:
        print("ERROR!")

    client.user_data_set(winkeKatze)

    while True:
        
        if not winkeKatze.isConnected:
            print("Arduino not connected.")
            if (gotDevicePath):
                winkeKatze.connect(devicePath, 9600)
            else:
                tryToConnectArduino(winkeKatze, "ttyACM", 5)
            if winkeKatze.isConnected:
                print("Reconnected!")
            else:
                time.sleep(1)

        client.loop()


if __name__ == "__main__":
    main()

