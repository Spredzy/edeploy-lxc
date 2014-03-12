#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Gonéri Le Bouder <goneri.lebouder@enovance.com>
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
edeploy-lxc binary
"""

import yaml
import subprocess
import os
import argparse
import libvirt

from host import Host
from network import Network
from config import Config


def stop(conf):
    print "Stopping..."
    conn = libvirt.open('lxc://')
    general = Config(conf['general'])
    networks = [Network(network) for network in conf['networks']]
    hosts = [Host(host, general, idx, [network for network in networks if network.name == host['network']][0]) for idx, host in enumerate(conf['hosts'])]

    for host in hosts:
        host.stop_domain(conn)
        host.remove_filesystem()

    for network in networks:
        network.undefine_network(conn)


def start(conf):

    conn = libvirt.open('lxc://')

    general = Config(conf['general'])
    roles = set([host['role'] for host in conf['hosts']])
    networks = [Network(network) for network in conf['networks']]
    hosts = [Host(host, general, idx,  [network for network in networks if network.name == host['network']][0]) for idx, host in enumerate(conf['hosts'])]
    hosts_map = ["%s %s.%s %s" % (host.ipv4, host.name, host.network.domain, host.name) for host in hosts]

    for network in networks:
        print "Setting up network (%s)... " % network
        network.define_network(conn)

    if not os.path.exists(general.lxc_dir):
        print "Creating directory %s..." % general.lxc_dir
        os.makedirs(general.lxc_dir)

    if not os.path.exists(general.tmp_dir):
        print "Creating directory %s..." % general.tmp_dir
        os.makedirs(general.tmp_dir)

    for role in roles:
        if not os.path.exists('%s/%s.qcow2' % (general.lxc_dir, role)):
            print "Creating role %s..." % role
            print "  * Creating empty image"
            subprocess.call(['dd', 'if=/dev/zero', "of=%s/%s.img" % (general.lxc_dir, role), 'bs=1G', 'count=8'])
            print "  * Formatting (ext4) empty image"
            subprocess.call(['mkfs.ext4', "%s/%s.img" % (general.lxc_dir, role)])
            if not os.path.exists("%s/%s" % (general.tmp_dir, role)):
                print "  * Creating temporary mount point %s/tmp-%s..." % (general.tmp_dir,role)
                os.makedirs("%s/tmp-%s" % (general.tmp_dir, role))
            print "  * Mounting empty image"
            subprocess.call(['mount', "%s/%s.img" % (general.lxc_dir, role), "%s/tmp-%s" % (general.tmp_dir, role)])
            print "  * Copying edeploy content from %s/%s to %s/tmp-%s" % (general.edeploy_dir, role, general.tmp_dir, role)
            os.system("cp -rcp %s/%s/* %s/tmp-%s/" % (general.edeploy_dir, role, general.tmp_dir, role))
            print "  * Unmounting %s/tmp-%s" % (general.tmp_dir, role)
            subprocess.call(['umount', "%s/tmp-%s" % (general.tmp_dir, role)])
            print "  * Creating base qcow2 file"
            subprocess.call(['qemu-img', 'convert', '-f', 'raw', '-O', 'qcow2', "%s/%s.img" % (general.lxc_dir, role), "%s/%s.qcow2" % (general.lxc_dir, role)])
            print "  * Removing img files"
            subprocess.call(['rm', '-f', "%s/%s.img" % (general.lxc_dir, role)])

    for host in hosts:
        print "Building host %s..." % host.name
        print "  * Creating filesystem"
        host.create_filesystem()
        print "  * Configuring ssh"
        host.setup_ssh_key()
        print "  * Configuring cloud init"
        #host.setup_cloudinit()
        print "  * Configuring network"
        host.setup_network(hosts_map)
        print "  * Starting domain"
        host.start_domain(conn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', help='action', choices=['stop', 'start', 'restart'])
    parser.add_argument('--config', help='configuration file', required=True)

    args = parser.parse_args()

    stream = file(args.config, 'r')
    conf = yaml.load(stream)

    if args.action == 'start':
        start(conf)
    elif args.action == 'stop':
        stop(conf)
    elif args.action == 'restart':
        stop(conf)
        start(conf)
