#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Yanis Guenane <yanis.guenane@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
"""

import uuid
import random


def random_mac():
    """Generate a random MAC address."""

    mac = [0x00, 0x16, 0x3e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


class Network(object):
    """A Network."""

    def __init__(self, network):
        self.name = network['name']
        self.network_type = network['type']
        self.gateway = network['gateway']
        self.domain = network['gateway']
        self.xml = self._get_network_xml()

    def _get_network_xml(self):

        xmlDesc = "<network>\n" + \
            "  <name>%s</name>\n" % self.name + \
            "  <uuid>%s</uuid>\n" % str(uuid.uuid4()) + \
            "  <forward mode='nat'>\n" + \
            "    <nat>\n" + \
            "      <port start='1024' end='65535'/>\n" + \
            "    </nat>\n" + \
            "  </forward>\n" + \
            "  <bridge name='%s' stp='on' delay='0' />\n" % self.name + \
            "  <mac address='%s'/>\n" % random_mac() + \
            "  <ip address='%s' netmask='255.255.255.0'>\n" % self.gateway + \
            "  </ip>\n" + \
            "</network>"

        return xmlDesc

    def define_network(self, conn):
        network = conn.networkDefineXML(self.xml)
        network.create()

    def undefine_network(self, conn):
        network = conn.networkLookupByName(self.name)
        network.destroy()
        network.undefine()
