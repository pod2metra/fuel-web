#    Copyright 2016 Mirantis, Inc.
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

"""Fuel 10.0

Revision ID: c6edea552f1e
Revises: 675105097a69
Create Date: 2016-04-08 15:20:43.989472

"""

from alembic import op
import sqlalchemy as sa

from nailgun.db.sqlalchemy.models import fields


# revision identifiers, used by Alembic.
revision = 'c6edea552f1e'
down_revision = 'f2314e5d63c9'


def upgrade():
    upgrade_plugin_links_constraints()
    upgrade_plugin_with_nics_and_nodes_attributes()


def downgrade():
    downgrade_plugin_with_nics_and_nodes_attributes()
    downgrade_plugin_links_constraints()


def upgrade_plugin_links_constraints():
    connection = op.get_bind()

    # plugin links
    plugin_links_remove_duplicates_query = sa.text("""
        DELETE FROM plugin_links
        WHERE id
        NOT IN (
          SELECT MIN(id)
          FROM plugin_links
          GROUP BY url
        )
    """)
    connection.execute(plugin_links_remove_duplicates_query)

    op.create_unique_constraint(
        'plugin_links_url_uc',
        'plugin_links',
        ['url'])

    # cluster plugin links
    cluster_plugin_links_remove_duplicates_query = sa.text("""
        DELETE FROM cluster_plugin_links
        WHERE id
        NOT IN (
          SELECT MIN(id)
          FROM cluster_plugin_links
          GROUP BY cluster_id,url
        )
    """)
    connection.execute(cluster_plugin_links_remove_duplicates_query)

    op.create_unique_constraint(
        'cluster_plugin_links_cluster_id_url_uc',
        'cluster_plugin_links',
        ['cluster_id', 'url'])


def downgrade_plugin_links_constraints():
    op.drop_constraint('cluster_plugin_links_cluster_id_url_uc',
                       'cluster_plugin_links')

    op.drop_constraint('plugin_links_url_uc', 'plugin_links')


def upgrade_plugin_with_nics_and_nodes_attributes():
    op.add_column(
        'plugins',
        sa.Column(
            'nic_attributes_metadata',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.add_column(
        'plugins',
        sa.Column(
            'bond_attributes_metadata',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.add_column(
        'plugins',
        sa.Column(
            'node_attributes_metadata',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.add_column(
        'node_nic_interfaces',
        sa.Column(
            'attributes',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.add_column(
        'node_nic_interfaces',
        sa.Column(
            'meta',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.add_column(
        'node_bond_interfaces',
        sa.Column(
            'attributes',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.add_column(
        'releases',
        sa.Column(
            'nic_attributes',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.add_column(
        'releases',
        sa.Column(
            'bond_attributes',
            fields.JSON(),
            nullable=False,
            server_default='{}'
        )
    )

    op.create_table(
        'node_nic_interface_cluster_plugins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'attributes', fields.JSON(), nullable=False, server_default='{}'),
        sa.Column('cluster_plugin_id', sa.Integer(), nullable=False),
        sa.Column('interface_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['cluster_plugin_id'],
            ['cluster_plugins.id'],
            ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['interface_id'], ['node_nic_interfaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['node_id'], ['nodes.id'], ondelete='CASCADE')
    )

    op.create_table(
        'node_bond_interface_cluster_plugins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'attributes', fields.JSON(), nullable=False, server_default='{}'),
        sa.Column('cluster_plugin_id', sa.Integer(), nullable=False),
        sa.Column('bond_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['cluster_plugin_id'],
            ['cluster_plugins.id'],
            ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['bond_id'], ['node_bond_interfaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['node_id'], ['nodes.id'], ondelete='CASCADE')
    )

    op.create_table(
        'node_cluster_plugins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'attributes', fields.JSON(), nullable=False, server_default='{}'),
        sa.Column('cluster_plugin_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['cluster_plugin_id'],
            ['cluster_plugins.id'],
            ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['node_id'], ['nodes.id'], ondelete='CASCADE')
    )


def downgrade_plugin_with_nics_and_nodes_attributes():
    op.drop_table('node_cluster_plugins')
    op.drop_table('node_bond_interface_cluster_plugins')
    op.drop_table('node_nic_interface_cluster_plugins')
    op.drop_column('releases', 'bond_attributes')
    op.drop_column('releases', 'nic_attributes')
    op.drop_column('node_bond_interfaces', 'attributes')
    op.drop_column('node_nic_interfaces', 'meta')
    op.drop_column('node_nic_interfaces', 'attributes')
    op.drop_column('plugins', 'node_attributes_metadata')
    op.drop_column('plugins', 'bond_attributes_metadata')
    op.drop_column('plugins', 'nic_attributes_metadata')
