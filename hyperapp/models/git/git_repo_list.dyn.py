import logging
from collections import defaultdict
from datetime import datetime
from functools import cached_property
from pathlib import Path

import pygit2

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark

log = logging.getLogger(__name__)


_REPO_LIST_PATH = 'git/repo-list.cdr'
_REPO_OBJECTS_FMT = 'git/{repo_name}-objects.cdr'


class Repository:

    def __init__(self, file_bundle_factory, data_dir, name, path):
        self._file_bundle_factory = file_bundle_factory
        self._data_dir = data_dir
        self.name = name
        self.path = path
        self._id_to_commit = {}  # Git id -> htypes.git.commit
        self._heads = []  # commit list
        self._head_commit_list = defaultdict(list)

    @property
    def object_count(self):
        return len(self._id_to_commit)

    @cached_property
    def repo(self):
        return pygit2.Repository(self.path)

    def head_commits(self, head_commit):
        return self._head_commit_list[head_commit]

    def get_commit(self, git_object):
        unloaded = {git_object}
        while unloaded:
            git_commit = unloaded.pop()
            if git_commit.id in self._id_to_commit:
                continue
            parents = []
            for git_parent in git_commit.parents:
                try:
                    parent_commit = self._id_to_commit[git_parent.id]
                except KeyError:
                    unloaded.add(git_parent)
                else:
                    parents.append(parent_commit)
            if len(parents) != len(git_commit.parents):
                unloaded.add(git_commit)
                continue
            commit = htypes.git.commit(
                id=str(git_commit.id),
                short_id=git_commit.short_id,
                parents=tuple(mosaic.put(p) for p in parents),
                time=datetime.fromtimestamp(git_commit.commit_time),
                author=str(git_commit.author),
                committer=str(git_commit.committer),
                message=git_commit.message,
                )
            self._id_to_commit[git_commit.id] = commit
        return self._id_to_commit[git_object.id]

    @property
    def _storage(self):
        path = self._data_dir / _REPO_OBJECTS_FMT.format(repo_name=self.name)
        return self._file_bundle_factory(path, encoding='cdr')

    def add_head(self, git_object):
        commit = self.get_commit(git_object)
        self._heads.append(commit)

    def save_objects(self):
        storage = htypes.git.storage(
            heads=tuple(
                mosaic.put(commit)for commit in self._heads
                ),
            )
        self._storage.save_piece(storage)
        log.info("Git: Saved %d objects to: %s", self.object_count, self._storage.path)

    def load_objects(self):
        log.info("Git: Loading repository %s: %s", self.name, self._storage.path)
        try:
            storage = self._storage.load_piece()
        except FileNotFoundError:
            return
        for ref in storage.heads:
            commit = self._cache_ref(ref)
            self._heads.append(commit)

    def _cache_ref(self, commit_ref):
        unprocessed = [commit_ref]
        while unprocessed:
            commit = web.summon(unprocessed.pop())
            if commit.id in self._id_to_commit:
                continue
            self._id_to_commit[commit.id] = commit
            for parent_ref in commit.parents:
                unprocessed.append(parent_ref)
        return commit


class RepoList:

    def __init__(self, file_bundle_factory, data_dir, file_bundle):
        self._file_bundle_factory = file_bundle_factory
        self._data_dir = data_dir
        self._file_bundle = file_bundle
        self._name_to_path = {}
        self._path_to_repo = {}

    def load(self):
        try:
            storage = self._file_bundle.load_piece()
        except FileNotFoundError:
            return
        for path_str in storage.path_list:
            path = Path(path_str)
            self._name_to_path[path.name] = path
            self._path_to_repo[path] = Repository(self._file_bundle_factory, self._data_dir, path.name, path)

    def _save(self):
        storage = htypes.git.repo_list_storage(
            path_list=tuple(str(p) for p in self._name_to_path.values()),
            )
        self._file_bundle.save_piece(storage)

    def items(self):
        return self._path_to_repo.values()

    def repo_by_dir(self, dir):
        return self._path_to_repo[Path(dir)]

    def enum_items(self):
        for repo in self.items():
            try:
                git_repo = repo.repo
            except pygit2.GitError as x:
                yield htypes.git.repo_item(
                    name=repo.name,
                    path=str(repo.path),
                    current_branch=str(x),
                    )
                continue
            try:
                current_branch = git_repo.head.shorthand
            except pygit2.GitError:
                current_branch = ''
            yield htypes.git.repo_item(
                name=repo.name,
                path=str(repo.path),
                current_branch=current_branch,
                )

    def add(self, path):
        self._name_to_path[path.name] = path
        self._path_to_repo[path] = Repository(self._file_bundle_factory, self._data_dir, path.name, path)
        self._save()
        return path.name

    def remove(self, name):
        path = self._name_to_path[name]
        del self._name_to_path[name]
        del self._path_to_repo[path]
        self._save()


@mark.service
def repo_list(file_bundle_factory, data_dir):
    file_bundle = file_bundle_factory(data_dir / _REPO_LIST_PATH, encoding='cdr')
    repo_list = RepoList(file_bundle_factory, data_dir, file_bundle)
    repo_list.load()
    return repo_list


@mark.model(key='name')
def repo_list_model(piece, repo_list):
    return list(repo_list.enum_items())


@mark.command.add(args=['path'])
def add(piece, path, repo_list):
    if not path:
        return
    repo_name = repo_list.add(Path('/', *path.parts))
    return repo_name


@mark.command.remove
def remove(piece, current_key, repo_list):
    if not current_key:
        return
    repo_list.remove(current_key)
    return True


@mark.command(preserve_remote=True)
def refs(piece, current_item):
    return htypes.git.ref_list_model(
        repo_name=current_item.name,
        repo_dir=current_item.path,
        )


@mark.global_command
def open_repo_list():
    return htypes.git.repo_list_model()


@mark.actor.formatter_creg
def format_model(piece):
    return "Git repositories"


@mark.init_hook
def load_repositories(repo_list):
    for repo in repo_list.items():
        repo.load_objects()
        obj_count = repo.object_count
        log.info("Git: Loaded %d objects; loading missing git objects", obj_count)
        for ref in repo.repo.references.objects:
            repo.add_head(ref.peel())
        log.info("Git: Loaded %d new objects", repo.object_count - obj_count)
        repo.save_objects()
