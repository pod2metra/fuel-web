# -*- coding: utf-8 -*-

#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import multiprocessing.dummy

from nailgun import consts
from nailgun import errors
from nailgun import lcm
from nailgun.utils.role_resolver import RoleResolver

from nailgun.test.base import BaseUnitTest


class TestTransactionSerializer(BaseUnitTest):
    @classmethod
    def setUpClass(cls):
        cls.tasks = [
            {
                'id': 'task1', 'roles': ['controller'],
                'type': 'puppet', 'version': '2.0.0',
                'condition': {
                    'yaql_exp': '$.public_ssl.hostname = localhost'
                },
                'parameters': {},
                'requires': ['task3'],
                'required_for': ['task2'],
                'cross_depends': [{'name': 'task2', 'role': 'compute'}],
                'cross_depended_by': [{'name': 'task3', 'role': 'cinder'}]
            },
            {
                'id': 'task2', 'roles': ['compute', 'controller'],
                'type': 'puppet', 'version': '2.0.0',
                'condition': {
                    'yaql_exp': '$.public_ssl.hostname != localhost'
                },
                'parameters': {},
                'cross_depends': [{'name': 'task3', 'role': 'cinder'}]
            },
            {
                'id': 'task3', 'roles': ['cinder', 'controller'],
                'type': 'puppet', 'version': '2.0.0',
                'condition': 'settings:public_ssl.hostname != "localhost"',
                'parameters': {},
                'cross_depends': [{'name': 'task3', 'role': '/.*/'}],
                'cross_depended_by': [{'name': 'task2', 'role': 'self'}]
            },
            {
                'id': 'task4', 'roles': ['controller'],
                'type': 'puppet', 'version': '2.0.0',
                'parameters': {},
                'cross_depended_by': [{'name': 'task3'}]
            }
        ]

        cls.nodes = [
            mock.MagicMock(uid='1', roles=['controller']),
            mock.MagicMock(uid='2', roles=['compute']),
            mock.MagicMock(uid='3', roles=['cinder']),
            mock.MagicMock(uid='4', roles=['custom']),
        ]

        cls.context = lcm.TransactionContext({
            '1': {
                'cluster': {'id': 1},
                'release': {'version': 'liberty-9.0'},
                'openstack_version': 'liberty-9.0',
                'public_ssl': {'hostname': 'localhost'},
                'attributes': {
                    'a_str': 'text1',
                    'a_int': 1
                }
            },
            '2': {
                'cluster': {'id': 1},
                'release': {'version': 'liberty-9.0'},
                'openstack_version': 'liberty-9.0',
                'public_ssl': {'hostname': 'localhost'},
                'attributes': {
                    'a_str': 'text2',
                    'a_int': 2
                }
            },
            '3': {
                'cluster': {'id': 1},
                'release': {'version': 'liberty-9.0'},
                'openstack_version': 'liberty-9.0',
                'public_ssl': {'hostname': 'localhost'},
                'attributes': {
                    'a_str': 'text3',
                    'a_int': 3
                }
            },
            '4': {
                'cluster': {'id': 1},
                'release': {'version': 'liberty-9.0'},
                'openstack_version': 'liberty-9.0',
                'public_ssl': {'hostname': 'localhost'},
                'attributes': {
                    'a_str': 'text3',
                    'a_int': 3
                }
            }
        })

        with mock.patch('nailgun.utils.role_resolver.objects') as m_objects:
            m_objects.Node.all_roles = lambda x: x.roles
            cls.role_resolver = RoleResolver(cls.nodes)

    def test_serialize_integration(self):
        serialized = lcm.TransactionSerializer.serialize(
            self.context, self.tasks, self.role_resolver
        )[1]
        # controller
        self.datadiff(
            [
                {
                    'id': 'task1', 'type': 'puppet', 'fail_on_error': True,
                    'parameters': {},
                    'requires': [
                        {'node_id': '1', 'name': 'task3'},
                        {'node_id': '2', 'name': 'task2'},
                    ],
                    'required_for': [
                        {'node_id': '1', 'name': 'task2'},
                        {'node_id': '3', 'name': 'task3'},
                    ]
                },
                {
                    'id': 'task2', 'type': 'skipped', 'fail_on_error': False,
                    'requires': [
                        {'node_id': '3', 'name': 'task3'},
                    ],
                },
                {
                    'id': 'task3', 'type': 'skipped', 'fail_on_error': False,
                    'requires': [
                        {'node_id': '3', 'name': 'task3'},
                    ],
                    'required_for': [
                        {'node_id': '1', 'name': 'task2'},
                    ]
                },
                {
                    'id': 'task4', 'type': 'puppet', 'fail_on_error': True,
                    'parameters': {},
                    'required_for': [
                        {'node_id': '1', 'name': 'task3'},
                        {'node_id': '3', 'name': 'task3'},
                    ]
                }

            ],
            serialized['1'],
            ignore_keys=['parameters', 'fail_on_error'],
            compare_sorted=True,
        )
        # compute
        self.datadiff(
            [
                {
                    'id': 'task2', 'type': 'skipped', 'fail_on_error': True,
                    'requires': [
                        {'node_id': '3', 'name': 'task3'},
                    ],
                }
            ],
            serialized['2'],
            ignore_keys=['parameters', 'fail_on_error'],
            compare_sorted=True,
        )
        # cinder
        self.datadiff(
            [
                {
                    'id': 'task3', 'type': 'skipped', 'fail_on_error': True,
                    'requires': [
                        {'node_id': '1', 'name': 'task3'},
                    ]
                }
            ],
            serialized['3'],
            ignore_keys=['parameters', 'fail_on_error'],
            compare_sorted=True,
        )

    def test_resolve_nodes(self):
        serializer = lcm.TransactionSerializer(
            self.context, self.role_resolver
        )
        self.assertEqual(
            [None],
            serializer.resolve_nodes(
                {'id': 'deploy_start',
                 'type': consts.ORCHESTRATOR_TASK_TYPES.stage}
            )
        )
        self.assertItemsEqual(
            ['2'],
            serializer.resolve_nodes(
                {'id': 'deploy_start',
                 'type': consts.ORCHESTRATOR_TASK_TYPES.skipped,
                 'groups': ['compute']},
            )
        )
        self.assertItemsEqual(
            ['1'],
            serializer.resolve_nodes(
                {'id': 'deploy_start',
                 'type': consts.ORCHESTRATOR_TASK_TYPES.skipped,
                 'roles': ['controller']}
            )
        )

    def test_dependencies_de_duplication(self):
        serializer = lcm.TransactionSerializer(
            self.context, self.role_resolver
        )
        serializer.tasks_graph = {
            None: {},
            '1': {
                'task1': {
                    'id': 'task1',
                    'requires': ['task2'],
                    'cross_depends': [
                        {'role': 'self', 'name': 'task2'},
                    ]
                },
                'task2': {
                    'id': 'task2',
                    'required_for': ['task1'],
                    'cross_depended_by': [{'role': 'self', 'name': 'task1'}]
                }
            }
        }
        serializer.resolve_dependencies()
        self.datadiff(
            {
                'task1': {
                    'id': 'task1',
                    'requires': [{'node_id': '1', 'name': 'task2'}],
                },
                'task2': {
                    'id': 'task2',
                    'required_for': [{'node_id': '1', 'name': 'task1'}],
                }
            },
            serializer.tasks_graph['1'],
            compare_sorted=True
        )

    def test_tasks_expand_groups(self):
        tasks = list(self.tasks)
        tasks.append({
            'id': 'task4', 'roles': ['/.*/'],
            'type': 'puppet', 'version': '2.0.0',
            'parameters': {},
            'cross_depends': [{'name': 'task2', 'role': 'self'}],
        })
        tasks.append({
            'id': 'custom', 'type': 'group', 'roles': 'custom',
            'fault_tolerance': '100%',
            'tasks': ['task4', 'task2']
        })
        tasks.append({
            'id': 'controller', 'type': 'group', 'roles': 'controller',
            'fault_tolerance': '0%',
            'tasks': ['task4', 'task2']
        })
        tasks.append({
            'id': 'compute', 'type': 'group', 'roles': 'compute',
            'tasks': ['task4', 'task2']
        })
        serialized = lcm.TransactionSerializer.serialize(
            self.context, tasks, self.role_resolver
        )
        tasks_per_node = serialized[1]
        self.datadiff(
            [
                {
                    'id': 'task2', 'type': 'skipped', 'fail_on_error': True,
                    'requires': [{'name': 'task3', 'node_id': '3'}]

                },
                {
                    'id': 'task4', 'type': 'puppet', 'fail_on_error': True,
                    'parameters': {},
                    'requires': [{'name': 'task2', 'node_id': '4'}]

                },
            ],
            tasks_per_node['4'],
            ignore_keys=['parameters', 'fail_on_error'],
            compare_sorted=True
        )

        tasks_metadata = serialized[2]
        self.datadiff(
            {
                'fault_tolerance_groups': [
                    {
                        'name': 'custom',
                        'node_ids': ['4'],
                        'fault_tolerance': 1
                    },
                    {
                        'name': 'controller',
                        'node_ids': ['1'],
                        'fault_tolerance': 0
                    },
                    {
                        'name': 'compute',
                        'node_ids': ['2'],
                        'fault_tolerance': 2
                    }
                ]
            },
            tasks_metadata,
            compare_sorted=True
        )

    def test_expand_dependencies(self):
        serializer = lcm.TransactionSerializer(
            self.context, self.role_resolver
        )
        serializer.tasks_graph = {
            '1': {'task1': {}},
            '2': {'task2': {}},
            None: {'deploy_start': {}, 'deploy_end': {}}
        }
        self.assertItemsEqual([], serializer.expand_dependencies('1', None))
        self.assertItemsEqual([], serializer.expand_dependencies('1', []))
        self.assertItemsEqual(
            [('deploy_start', None), ('task2', '2')],
            serializer.expand_dependencies('2', ['deploy_start', 'task2'])
        )

    def test_expand_cross_dependencies(self):
        serializer = lcm.TransactionSerializer(
            self.context, self.role_resolver
        )
        serializer.tasks_graph = {
            '1': {'task1': {}, 'task2': {}},
            '2': {'task3': {}, 'task2': {}, 'task1': {}},
            '3': {'task3': {}},
            None: {'deploy_start': {}, 'deploy_end': {}}
        }
        self.assertItemsEqual(
            [], serializer.expand_cross_dependencies('task1', '1', None)
        )
        self.assertItemsEqual(
            [], serializer.expand_cross_dependencies('task1', '1', [])
        )

        self.assertItemsEqual(
            [
                ('deploy_start', None), ('task2', '2'),
                ('task3', '2'), ('task3', '3')
            ],
            serializer.expand_cross_dependencies(
                'task2', '1',
                [{'name': 'deploy_start', 'role': None},
                 {'name': 'task2', 'role': '/.*/'},
                 {'name': 'task3', 'role': '/.*/'}]
            )
        )
        self.assertItemsEqual(
            [('task2', '2'), ('task1', '1')],
            serializer.expand_cross_dependencies(
                'task2', '1',
                [{'name': 'task2'},
                 {'name': 'task1', 'role': 'self'}]
            )
        )

    def test_need_update_task(self):
        serializer = lcm.TransactionSerializer(
            self.context, self.role_resolver
        )
        self.assertTrue(serializer.need_update_task(
            {}, {"id": "task1", "type": "puppet"}
        ))
        self.assertTrue(serializer.need_update_task(
            {"task1": {"type": "skipped"}}, {"id": "task1", "type": "puppet"}
        ))

        self.assertFalse(serializer.need_update_task(
            {"task1": {"type": "skipped"}}, {"id": "task1", "type": "skipped"}
        ))

        self.assertFalse(serializer.need_update_task(
            {"task1": {"type": "puppet"}}, {"id": "task1", "type": "skipped"}
        ))

    @mock.patch(
        'nailgun.lcm.transaction_serializer.settings.LCM_CHECK_TASK_VERSION',
        new=True
    )
    def test_ensure_task_based_deploy_allowed_raises_if_version_check(self):
        self.assertRaises(
            errors.TaskBaseDeploymentNotAllowed,
            lcm.TransactionSerializer.ensure_task_based_deploy_allowed,
            {'type': consts.ORCHESTRATOR_TASK_TYPES.puppet,
             'version': '1.0.0', 'id': 'test'}
        )

    @mock.patch(
        'nailgun.lcm.transaction_serializer.settings.LCM_CHECK_TASK_VERSION',
        new=False
    )
    def test_ensure_task_based_deploy_allowed_if_not_version_check(self):
        self.assertNotRaises(
            errors.TaskBaseDeploymentNotAllowed,
            lcm.TransactionSerializer.ensure_task_based_deploy_allowed,
            {'type': consts.ORCHESTRATOR_TASK_TYPES.puppet,
             'version': '1.0.0', 'id': 'test'}
        )

    @mock.patch(
        'nailgun.lcm.transaction_serializer.settings'
        '.LCM_SERIALIZERS_CONCURRENCY_FACTOR',
        new=2
    )
    @mock.patch(
        'nailgun.lcm.transaction_serializer.multiprocessing',
        new=multiprocessing.dummy
    )
    def test_multi_processing_serialization(self):
        self.test_serialize_integration()

    def test_get_fault_tolerance(self):
        self.assertEqual(
            11,
            lcm.TransactionSerializer.calculate_fault_tolerance(None, 10)
        )
        self.assertEqual(
            10,
            lcm.TransactionSerializer.calculate_fault_tolerance('10', 10)
        )
        self.assertEqual(
            10,
            lcm.TransactionSerializer.calculate_fault_tolerance(10, 10)
        )
        self.assertEqual(
            1,
            lcm.TransactionSerializer.calculate_fault_tolerance('10%', 10)
        )
        self.assertEqual(
            11,
            lcm.TransactionSerializer.calculate_fault_tolerance('a%', 10)
        )
        self.assertEqual(
            9,
            lcm.TransactionSerializer.calculate_fault_tolerance(' -10%', 10)
        )
        self.assertEqual(
            9,
            lcm.TransactionSerializer.calculate_fault_tolerance('-1 ', 10)
        )
