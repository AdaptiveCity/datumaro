
# Copyright (C) 2019-2020 Intel Corporation
#
# SPDX-License-Identifier: MIT

from datumaro.components.config import Config, \
    DefaultConfig as _DefaultConfig, \
    SchemaBuilder as _SchemaBuilder


SOURCE_SCHEMA = _SchemaBuilder() \
    .add('url', str) \
    .add('format', str) \
    .add('options', dict) \
    .build()

class Source(Config):
    def __init__(self, config=None):
        super().__init__(config, schema=SOURCE_SCHEMA)


MODEL_SCHEMA = _SchemaBuilder() \
    .add('launcher', str) \
    .add('options', dict) \
    .build()

class Model(Config):
    def __init__(self, config=None):
        super().__init__(config, schema=MODEL_SCHEMA)


BUILDSTAGE_SCHEMA = _SchemaBuilder() \
    .add('name', str) \
    .add('type', str) \
    .add('parameters', str) \
    .build()

class BuildStage(Config):
    def __init__(self, config=None):
        super().__init__(config, schema=BUILDSTAGE_SCHEMA)

BUILDTARGET_SCHEMA = _SchemaBuilder() \
    .add('stages', list) \
    .add('parents', list) \
    .build()

class BuildTarget(Config):
    def __init__(self, config=None):
        super().__init__(config, schema=BUILDTARGET_SCHEMA)

    @property
    def root(self):
        return self.stages[0]

    @property
    def head(self):
        return self.stages[-1]


PROJECT_SCHEMA = _SchemaBuilder() \
    .add('project_name', str) \
    .add('format_version', int) \
    \
    .add('sources', lambda: _DefaultConfig(lambda v=None: Source(v))) \
    .add('models', lambda: _DefaultConfig(lambda v=None: Model(v))) \
    .add('build_targets', lambda: _DefaultConfig(lambda v=None: BuildTarget(v))) \
    \
    .add('models_dir', str, internal=True) \
    .add('plugins_dir', str, internal=True) \
    .add('sources_dir', str, internal=True) \
    .add('dataset_dir', str, internal=True) \
    .add('project_filename', str, internal=True) \
    .add('project_dir', str, internal=True) \
    .add('env_dir', str, internal=True) \
    .add('detached', bool, internal=True) \
    .build()

PROJECT_DEFAULT_CONFIG = Config({
    'project_name': 'undefined',
    'format_version': 1,

    'sources_dir': 'sources',
    'dataset_dir': 'dataset',
    'models_dir': 'models',
    'plugins_dir': 'plugins',

    'project_filename': 'config.yaml',
    'project_dir': '',
    'env_dir': '.datumaro',
    'detached': False,
}, mutable=False, schema=PROJECT_SCHEMA)
