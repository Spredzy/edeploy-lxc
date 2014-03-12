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

import subprocess
import os
import shutil


class Host(object):
    """A Host."""

    def __init__(self, host, general, idx, network):
        self.idx = idx + 3
        self.name = host['name']
        self.ipv4 = host['address']
        self.role = host['role']
        self.memory = host['memory']
        self.vcpu = host['vcpu']
        #self.cloudinit = host['cloudinit']
        self.ssh_key = general.ssh_key
        self.network = network
        self.config = general
        self.xml = self._get_domain_xml()

    def _get_domain_xml(self):

        xmlDesc = "<domain type='lxc'>\n" + \
            "  <name>%s</name>\n" % self.name + \
            "  <memory unit='MB'>%s</memory>\n" % self.memory + \
            "  <os>\n" + \
            "    <type>exe</type>\n" + \
            "    <init>/sbin/init</init>\n" + \
            "  </os>\n" + \
            "  <vcpu>%s</vcpu>\n" % self.vcpu + \
            "  <clock offset='utc'/>\n" + \
            "  <on_poweroff>destroy</on_poweroff>\n" + \
            "  <on_reboot>restart</on_reboot>\n" + \
            "  <on_crash>destroy</on_crash>\n" + \
            "  <devices>\n" + \
            "    <emulator>/usr/libexec/libvirt_lxc</emulator>\n" + \
            "      <filesystem type='mount'>\n" + \
            "        <source dir='/var/lib/lxc/%s'/>\n" % self.name + \
            "        <target dir='/'/>\n" + \
            "      </filesystem>\n" + \
            "    <interface type='network'>\n" + \
            "      <source network='%s'/>\n" % self.network.name + \
            "    </interface>\n" + \
            "    <console type='pty' />\n" + \
            "  </devices>\n" + \
            "</domain>"

        return xmlDesc

    def create_filesystem(self):
        subprocess.call(['qemu-img', 'create', '-f', 'qcow2', '-b', "%s/%s.qcow2" % (self.config.lxc_dir, self.role), "%s/%s.qcow2" % (self.config.lxc_dir, self.name)])
        if not os.path.exists("%s/%s" % (self.config.lxc_dir, self.name)):
            print "  * Creating temporary mount point %s/%s..." % (self.config.lxc_dir, self.name)
            os.makedirs("%s/%s" % (self.config.lxc_dir, self.name))
        subprocess.call(['qemu-nbd', '-c', "/dev/nbd%s" % self.idx, "%s/%s.qcow2" % (self.config.lxc_dir, self.name)])
        subprocess.call(['mount', "/dev/nbd%s" % self.idx, "%s/%s" % (self.config.lxc_dir, self.name)])
        print "  * Creating proc mount point %s/%s/proc..." % (self.config.lxc_dir, self.name)
        #subprocess.call(['mount', '-t', 'proc', 'proc', "%s/%s/proc" % (self.config.lxc_dir, self.name)])

    def remove_filesystem(self):
        #subprocess.call(['umount', "%s/%s/proc" % (self.config.lxc_dir, self.name)])
        subprocess.call(['umount', "%s/%s" % (self.config.lxc_dir, self.name)])
        subprocess.call(['qemu-nbd', '-d', "/dev/nbd%s" % self.idx])
        os.remove("%s/%s.qcow2" % (self.config.lxc_dir, self.name))
        shutil.rmtree("%s/%s" % (self.config.lxc_dir, self.name))

    def setup_ssh_key(self):
        if not self.ssh_key:
            return

        ssh_dir = "%s/%s/root/.ssh/" % (self.config.lxc_dir, self.name)
        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir)
        print "  * Copying %s to %s/authorized_keys" % (self.ssh_key, ssh_dir)
        shutil.copyfile(self.ssh_key, "%s/authorized_keys" % ssh_dir)
        #shutil.copyfile('/root/.ssh/id_rsa.pub', "%s/authorized_keys" % ssh_dir)

    def setup_cloudinit(self):
        print ">>>> Debug"
        #if not self.cloudinit:
        #    return
        print ' Cloudinit: %s' % self.cloudinit

        nocloud_dir = '%s/%s/var/lib/cloud/seed/nocloud' % (self.config.lxc_dir, self.name)
        print ' Cloudinit: %s' % nocloud_dir
        if not os.path.exists(nocloud_dir):
            os.makedirs(nocloud_dir)
            
        open(os.path.join(nocloud_dir, 'user-data'), 'w').write(open(self.cloudinit).read())
        open(os.path.join(nocloud_dir, 'meta-data'), 'w').write('local-hostname: %s' % self.name)

        if not os.path.exists('%s/%s/etc/cloud/cloud.cfg.d' % (self.config.lxc_dir, self.name)):
            os.makedirs('%s/%s/etc/cloud/cloud.cfg.d' % (self.config.lxc_dir, self.name))
              

        open('%s/%s/etc/cloud/cloud.cfg.d/90_dpkg.cfg' % (self.config.lxc_dir, self.name), 'w').write('''
          dsmod: local

          datasource_list: [ NoCloud ]
        ''')

    def _setup_hostname(self):
        hostnameFd = open('%s/%s/etc/hostname' % (self.config.lxc_dir, self.name), 'w')
        hostnameFd.write("%s" % self.name)
        hostnameFd.close()

    def _setup_interface(self):
        debian_interfaces = '%s/%s/etc/network/interfaces' % (self.config.lxc_dir, self.name)
        netFd = open(debian_interfaces, 'w')
        netFd.write("auto lo\n" +
                    "iface lo inet loopback\n" +
                    "auto eth0\n" +
                    "iface eth0 inet static\n" +
                    "    address %s\n" % self.ipv4 +
                    "    netmask 255.255.255.0\n" +
                    "    gateway %s\n" % self.network.gateway)
        netFd.close()

    def _setup_host_file(self):
        hostFd = open('%s/%s/etc/hosts' % (self.config.lxc_dir, self.name), 'w')
        hostFd.write(
            "127.0.0.1 %s.%s %s localhost\n" % (self.name, self.network.domain, self.name) +
            "::1     localhost ip6-localhost ip6-loopback\n" +
            "ff02::1 ip6-allnodes\n" +
            "ff02::2 ip6-allrouters\n"
        )
        hostFd.close()

    def _inject_hosts_map(self, hosts_map):
        hostFd = open('%s/%s/etc/hosts' % (self.config.lxc_dir, self.name), 'a')
        for entry in hosts_map:
            hostFd.write("%s\n" % entry)
        hostFd.close()

    def setup_network(self, hosts_map):
        self._setup_hostname()
        self._setup_interface()
        self._setup_host_file()
        self._inject_hosts_map(hosts_map)

    def start_domain(self, conn):
        domain = conn.defineXML(self.xml)
        domain.create()

    def stop_domain(self, conn):
        domain = conn.lookupByName(self.name)
        domain.destroy()
        domain.undefine()

