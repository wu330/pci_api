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

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
from nova import db
from nova.objects import instance as instance_obj
from nova.objects import pci_device


instance_authorize = extensions.soft_extension_authorizer(
    'compute', 'instance_pci')
authorize = extensions.soft_extension_authorizer('compute', 'pci')


class Pci(extensions.ExtensionDescriptor):
    """Pci access support."""
    name = "pcis"
    alias = "os-pci"
    namespace = "http://docs.openstack.org/compute/ext/pci/api/v1.1"
    updated = "2012-06-21T00:00:00+00:00"

    def get_resources(self):
        resources = [extensions.ResourceExtension('os-pci',
                     PciController(),
                     collection_actions={'detail': 'GET'},
                     member_actions={'pci_devices': 'GET'})]
        return resources

    def get_controller_extensions(self):
        server_extension = extensions.ControllerExtension(
            self, 'servers', PciServerController())
        compute_extension = extensions.ControllerExtension(
            self, 'os-hypervisors', PciHypervisorController())
        return [server_extension, compute_extension]


def make_server(elem):
    elem.set('{%s}pci_info' % Pci.namespace,
             '%s:pci' % Pci.alias)


class PciServerTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('server', selector='server')
        make_server(root)
        return xmlutil.SlaveTemplate(root, 1, nsmap={
            Pci.alias: Pci.namespace})


class PciServersTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('servers')
        elem = xmlutil.SubTemplateElement(root, 'server', selector='servers')
        make_server(elem)
        return xmlutil.SlaveTemplate(root, 1, nsmap={
            Pci.alias: Pci.namespace})


class PciServerController(wsgi.Controller):
    def __init__(self, *args, **kwargs):
        super(PciServerController, self).__init__(*args, **kwargs)

    def _extend_server(self, server, instance):
        dev_id = []
        for dev in instance.pci_devices:
            dev_id.append(dev['id'])
        server['%s:pci' % Pci.alias] = dev_id

    @wsgi.extends
    def show(self, req, resp_obj, id):
        context = req.environ['nova.context']
        if instance_authorize(context):
            # Attach our slave template to the response object
            resp_obj.attach(xml=PciServerTemplate())
            server = resp_obj.obj['server']
            instance = instance_obj.Instance.get_by_uuid(
                context, server['id'], expected_attrs='pci_devices')
            self._extend_server(server, instance)

    @wsgi.extends
    def detail(self, req, resp_obj):
        context = req.environ['nova.context']
        if instance_authorize(context):
            # Attach our slave template to the response object
            resp_obj.attach(xml=PciServersTemplate())
            servers = list(resp_obj.obj['servers'])
            for server in servers:
                instance = instance_obj.Instance.get_by_uuid(
                    context, server['id'], expected_attrs='pci_devices')
                self._extend_server(server, instance)


def make_hypervisor(elem):
    elem.set('{%s}pci_info' % Pci.namespace,
             '%s:pci' % Pci.alias)


class PciHypervisorTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('hypervisor', selector='hypervisor')
        make_hypervisor(root)
        return xmlutil.SlaveTemplate(root, 1, nsmap={
            Pci.alias: Pci.namespace})


class PciHypervisorController(wsgi.Controller):
    def __init__(self, *args, **kwargs):
        super(PciHypervisorController, self).__init__(*args, **kwargs)

    def _extend_hypervisor(self, hypervisor, compute_node):
        hypervisor['%s:pci_stats' % Pci.alias] = compute_node['pci_stats']

    @wsgi.extends
    def show(self, req, resp_obj, id):
        context = req.environ['nova.context']
        resp_obj.attach(xml=PciHypervisorTemplate())
        hypervisor = resp_obj.obj['hypervisor']
        # TODO(yjiang5): Change to compute node object after that change merged
        #compute_node = compute_obj.ComputeNode.get_by_id(
        #    context, hypervisor['id'])
        compute_node = db.compute_node_get(context, hypervisor['id'])
        self._extend_hypervisor(hypervisor, compute_node)

    @wsgi.extends
    def detail(self, req, resp_obj):
        context = req.environ['nova.context']
        hypervisors = list(resp_obj.obj['hypervisors'])
        for hypervisor in hypervisors:
            # TODO(yjiang5): Change to compute node object after
            # that changes merged
            # compute_node = compute_obj.ComputeNode.get_by_id(
            #    context, hypervisor['id'])
            compute_node = db.compute_node_get(context, hypervisor['id'])
            hypervisor['os-pci:pci_stats'] = compute_node['pci_stats']


def make_pcidev(elem, detail):
    elem.set('id')
    elem.set('host')
    elem.set('node')
    elem.set('address')
    if detail:
        elem.set('vendor_id')
        elem.set('product_id')
        elem.set('device_type')
        elem.set('status')
        elem.set('label')
        elem.set('instance_uuid')
        elem.set('hypervisor_name')


class PciIndexTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('pcis')
        elem = xmlutil.SubTemplateElement(root, 'pci',
                                          selector='pcis')
        make_pcidev(elem, False)
        return xmlutil.MasterTemplate(root, 1)


class PciDetailTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('pcis')
        elem = xmlutil.SubTemplateElement(root, 'pci',
                                          selector='pcis')
        make_pcidev(elem, True)
        return xmlutil.MasterTemplate(root, 1)


class PciTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('pci', selector='pci')
        make_pcidev(root, True)
        return xmlutil.MasterTemplate(root, 1)


class PciController(object):
    def __init__(self):
        super(PciController, self).__init__()

    def _view_pcidevice(self, device, detail=False):
        dev_dict = {
            'id': device['id'],
            'vendor_id': device.vendor_id,
        }

        if detail:
            for field in pci_device.PciDevice.fields:
                dev_dict[field] = device[field]

        return dev_dict

    @wsgi.serializers(xml=PciDetailTemplate)
    def detail(self, req):
        context = req.environ['nova.context']
        authorize(context)
        pci_dev = pci_device.PciDevice.get_by_dev_id(context, 46)
        return dict(pcis=[self._view_pcidevice(pci_dev, True)])

    @wsgi.serializers(xml=PciTemplate)
    def show(self, req, id):
        context = req.environ['nova.context']
        authorize(context)
        pci_dev = pci_device.PciDevice.get_by_dev_id(context, id)
        result = self._view_pcidevice(pci_dev, True)
        return dict(pci=result)

    @wsgi.serializers(xml=PciIndexTemplate)
    def index(self, req):
        node = req.GET.get('node')
        context = req.environ['nova.context']
        authorize(context)
        pci_devs = pci_device.PciDeviceList.get_by_compute_node(context, node)
        return dict(pcis=[self._view_pcidevice(pci_dev, True)
                    for pci_dev in pci_devs])
