import collections.abc
import json
import os
import subprocess
from argparse import Namespace
from functools import partial

from git_annex_metadata_gui.models import GitAnnexField


class Process:
    def __init__(self, *batch_command, workdir=None):
        self._command = batch_command
        self._workdir = workdir
        self._process = self.start()

    def start(self):
        process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self._workdir,
        )
        return process

    def running(self):
        return self._process and self._process.poll() is None

    def terminate(self, kill=False):
        self._process.terminate()
        try:
            self._process.wait(5)
        except subprocess.TimeoutExpired:
            if kill:
                self._process.kill()
            else:
                raise

    def restart(self):
        if self.running():
            self.terminate()
            self._process = self.start()

    def query_json(self, **query):
        json_ = json.dumps(query)
        response = self.query_line(json_)
        return json.loads(response)

    def query_line(self, query):
        while not self.running():
            self._process = self.start()
        print(query, file=self._process.stdin, flush=True)
        return self._process.stdout.readline().strip()


class GitAnnex:
    def __init__(self, path):
        self.repo_path = subprocess.check_output(
            ('git', 'rev-parse', '--show-toplevel'),
            universal_newlines=True, cwd=path,
            stderr=subprocess.PIPE,
        ).strip()

        subprocess.check_output(
            ('git', 'annex', 'metadata', '--key', 'SHA256E-s0--0'),
            universal_newlines=True, cwd=path,
            stderr=subprocess.PIPE,
        )

        self.processes = Namespace()
        self.processes.metadata = Process(
            'git', 'annex', 'metadata', '--batch', '--json',
            workdir=self.repo_path
        )
        self.processes.locate = Process(
            'git', 'annex', 'contentlocation', '--batch',
            workdir=self.repo_path
        )

        self._meta_cache = None
        self._meta_all_cache = None

    def metadata(self, all=False, cached=False):
        cache = self._meta_all_cache if all else self._meta_cache
        if cached and cache:
            return cache

        try:
            jsons = subprocess.check_output(
                ('git', 'annex', 'metadata', '--json',
                 '--all' if all else ''),
                universal_newlines=True, cwd=self.repo_path,
                stderr=subprocess.PIPE,
            ).splitlines()
        except subprocess.CalledProcessError as err:
            return []
        else:
            metadata = [json.loads(json_) for json_ in jsons]
            if all:
                self._meta_all_cache = metadata
            else:
                self._meta_cache = metadata
            return metadata

    def keys(self, absent=False, cached=False):
        all_meta = self.metadata(cached=cached, all=True)
        all_keys = {meta['key'] for meta in all_meta}
        if absent:
            try:
                file_meta = self.metadata(cached=cached)
                file_keys = {meta['key'] for meta in file_meta}
                return all_keys - file_keys
            except subprocess.CalledProcessError:
                return all_keys
        else:
            return all_keys

    def files(self, cached=False):
        try:
            file_meta = self.metadata(cached=cached)
            return {meta['file'] for meta in file_meta}
        except subprocess.CalledProcessError:
            return {}

    def fields(self, cached=False):
        metadata = self.metadata(all=True, cached=cached)
        fields = [meta.get('fields', {}) for meta in metadata]
        return filter(
            lambda f: not f.endswith('lastchanged'),
            set.union(*map(set, fields + [{}]))
        )

    def item(self, key=None, path=None):
        if key:
            return GitAnnexFile(self, key, file=path)
        elif path:
            key = self.processes.metadata.query_json(file=path)['key']
            return GitAnnexFile(self, key, file=path)
        else:
            raise ValueError('Requires path or key')

    def locate(self, key, abs=False):
        rel_path = self.processes.locate.query_line(key)
        if abs:
            return os.path.join(self.repo_path, rel_path)
        else:
            return rel_path

    def __repr__(self):
        return 'GitAnnex(repo_path={!r})'.format(self.repo_path)


class GitAnnexFile(collections.abc.MutableMapping):
    def __init__(self, annex, key, file=None):
        self.key = key
        self.file = file
        self.annex = annex
        self.query = partial(
            self.annex.processes.metadata.query_json,
            key=key
        )
        self.locate = partial(self.annex.locate, self.key)
        self.field_items = {}
        self.fields_cache = None

    def _fields(self, **fields):
        if self.fields_cache and not fields:
            return self.fields_cache

        if not fields:
            new_fields = self.query().get('fields', {})
        else:
            new_fields = self.query(fields=fields).get('fields', {})

        for field, value in fields.items():
            new_value = new_fields.get(field, [])
            if set(new_value) != set(value):
                self.annex.processes.metadata.restart()
                new_fields = self.query(fields=fields).get('fields', {})
                break
        else:
            self.fields_cache = new_fields
            return new_fields

        for field, value in fields.items():
            new_value = new_fields.get(field, [])
            if set(new_value) != set(value):
                self.fields_cache = None
                raise KeyError(field)
        else:
            self.fields_cache = new_fields
            return new_fields

    def field(self, field):
        if field not in self.field_items:
            self.field_items[field] = GitAnnexField(self, field)
        return self.field_items[field]

    def __getitem__(self, meta_key):
        if meta_key == 'key':
            return [self.key]
        if meta_key == 'file':
            return [self.file]
        values = self._fields().get(meta_key, [])
        return values

    def __setitem__(self, meta_key, value):
        if meta_key not in ['key', 'file']:
            self._fields(**{meta_key: value})

    def __delitem__(self, meta_key):
        self._fields(**{meta_key: []})

    def __contains__(self, meta_key):
        return meta_key in self._fields()

    def __iter__(self):
        for field in self._fields().keys():
            if not field.endswith('lastchanged'):
                yield field

    def __len__(self):
        len([x for x in self])

    def __repr__(self):
        return 'GitAnnexFile(key={!r}, file={!r})'.format(
            self.key, self.file)
