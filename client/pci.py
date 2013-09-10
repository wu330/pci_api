# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Intel Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import urllib
import six
from novaclient import base
from novaclient import utils


def _find_pci(cs, info):
    """Get a hypervisor by name or ID."""
    return utils.find_resource(cs.pci, info)


@utils.arg('pci',
    metavar='<pci>',
    help='ID of the pci to show the details of.')
def do_pci_show(cs, args):
    """Display the details of the specified pci ."""
    pci = _find_pci(cs, args.pci)
    # Build up the dict
    info = pci._info.copy()

    utils.print_dict(info)


@utils.arg('node',
    metavar='<node>',
    help='Node ID of the compute node to show the PCI information.')
def do_pci_list(cs, args):
    search_ops = {'node':args.node}
    pcis = cs.pci.list(search_ops)
    utils.print_list(pcis,
                     ['ID', 'address', 'vendor_id', 'product_id', 'status'])


class PciDevice(base.Resource):
    NAME_ATTR = 'id'
    HUMAN_ID=True

    def __init__(self, manager, info, loaded=False):
        super(PciDevice, self).__init__(manager, info, loaded)

    def __repr__(self):
        return "<pci: %s>" % self.id


class PciManager(base.ManagerWithFind):
    resource_class = PciDevice

    def list(self, search_opts=None):
        """
        Get a list of pci devices
        """
        if search_opts is None:
            search_opts = {}
        qparams = {}

        for opt, val in six.iteritems(search_opts):
            if val:
                qparams[opt] = val

        query_string = "?%s" % urllib.urlencode(qparams) if qparams else ""
        return self._list('/os-pci%s' % query_string, 'pcis')

    def get(self, pci):
        """
        Get a specific hypervisor.
        """
        result = self._get("/os-pci/%s" % base.getid(pci),
                         "pci")
        return result
