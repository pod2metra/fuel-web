# -*- coding: utf-8 -*-
import json

from api.models import Network
from base import BaseHandlers
from base import reverse


class TestHandlers(BaseHandlers):
    def test_nets_empty(self):
        resp = self.app.get(
            reverse('NetworkCollectionHandler'),
            headers=self.default_headers,
            expect_errors=True
        )
        self.assertEquals(404, resp.status)

    def test_valid_nets_returned_after_cluster_create(self):
        cluster = self.create_cluster_api()
        resp = self.app.get(
            reverse('NetworkCollectionHandler'),
            headers=self.default_headers
        )
        self.assertEquals(200, resp.status)
        response = json.loads(resp.body)

        expected = [
            {
                'id': 1,
                'name': u'floating',
                'cluster_id': cluster['id'],
                'vlan_id': 100,
                'cidr': '240.0.0.0/24',
                'gateway': '240.0.0.1'
            },
            {
                'id': 2,
                'name': u'fixed',
                'cluster_id': cluster['id'],
                'vlan_id': 101,
                'cidr': '10.0.0.0/24',
                'gateway': '10.0.0.1'
            },
            {
                'id': 3,
                'name': u'storage',
                'cluster_id': cluster['id'],
                'vlan_id': 102,
                'cidr': '192.168.0.0/24',
                'gateway': '192.168.0.1'
            },
            {
                'id': 4,
                'name': u'management',
                'cluster_id': cluster['id'],
                'vlan_id': 103,
                'cidr': '172.16.0.0/24',
                'gateway': '172.16.0.1'
            },
            {
                'id': 5,
                'name': u'other_172',
                'cluster_id': cluster['id'],
                'vlan_id': 104,
                'cidr': '172.16.1.0/24',
                'gateway': '172.16.1.1'
            },
        ]
        self.assertEquals(expected, response)

    def test_get_networks_by_cluster_id(self):
        cluster1 = self.create_cluster_api()
        cluster2 = self.create_cluster_api()
        nets_len = len(
            self.db.query(Network).filter(
                Network.cluster_id == cluster1['id']).all())

        resp = self.app.get(
            reverse('NetworkCollectionHandler'),
            params={'cluster_id': cluster1['id']},
            headers=self.default_headers
        )
        self.assertEquals(200, resp.status)
        nets_received = json.loads(resp.body)
        self.assertEquals(nets_len, len(nets_received))

    def test_networks_update_new_vlan_id(self):
        cluster = self.create_cluster_api()
        net1 = self.db.query(Network).first()
        new_vlan_id = 500  # non-used vlan id
        new_nets = [{
            'id': net1.id,
            'vlan_id': new_vlan_id}]
        resp = self.app.put(
            reverse('NetworkCollectionHandler'),
            json.dumps(new_nets),
            headers=self.default_headers
        )
        self.assertEquals(200, resp.status)
        nets_received = json.loads(resp.body)
        self.assertEquals(1, len(nets_received))
        expected_network = {
            'name': net1.name,
            'id': net1.id,
            'cluster_id': net1.cluster_id,
            'cidr': net1.cidr,
            'gateway': net1.gateway,
            'vlan_id': new_vlan_id,
        }
        self.assertEquals(expected_network, nets_received[0])

    def test_networks_update_fails_with_wrong_net_id(self):
        new_nets = [{
            'id': 500,
            'vlan_id': 500}]
        resp = self.app.put(
            reverse('NetworkCollectionHandler'),
            json.dumps(new_nets),
            headers=self.default_headers,
            expect_errors=True
        )
        self.assertEquals(400, resp.status)
