# coding: utf-8

from __future__ import unicode_literals, absolute_import

import os
import pytest
import tempfile
import fmf.utils as utils
import fmf.cli
from fmf.base import Tree
from shutil import rmtree


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Prepare path to examples
PATH = os.path.dirname(os.path.realpath(__file__))
EXAMPLES = PATH + "/../../examples/"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tree
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TestTree(object):
    """ Tree class """

    def setup_method(self, method):
        """ Load examples """
        self.wget = Tree(EXAMPLES + "wget")
        self.merge = Tree(EXAMPLES + "merge")

    def test_basic(self):
        """ No directory path given """
        with pytest.raises(utils.GeneralError):
            Tree("")
        with pytest.raises(utils.GeneralError):
            Tree(None)
        with pytest.raises(utils.RootError):
            Tree("/")

    def test_hidden(self):
        """ Hidden files and directories """
        assert(".hidden" not in self.wget.children)

    def test_inheritance(self):
        """ Inheritance and data types """
        deep = self.wget.find('/recursion/deep')
        assert(deep.data['depth'] == 1000)
        assert(deep.data['description'] == 'Check recursive download options')
        assert(deep.data['tags'] == ['Tier2'])

    def test_scatter(self):
        """ Scattered files """
        scatter = Tree(EXAMPLES + "scatter").find("/object")
        assert(len(list(scatter.climb())) == 1)
        assert(scatter.data['one'] == 1)
        assert(scatter.data['two'] == 2)
        assert(scatter.data['three'] == 3)

    def test_scattered_inheritance(self):
        """ Inheritance of scattered files """
        grandson = Tree(EXAMPLES + "child").find("/son/grandson")
        assert(grandson.data['name'] == 'Hugo')
        assert(grandson.data['eyes'] == 'blue')
        assert(grandson.data['nose'] == 'long')
        assert(grandson.data['hair'] == 'fair')

    def test_subtrees(self):
        """ Subtrees should be ignored """
        child = Tree(EXAMPLES + "child")
        assert child.find("/nobody") is None

    def test_empty(self):
        """ Empty structures should be ignored """
        child = Tree(EXAMPLES + "empty")
        assert child.find("/nothing") is None
        assert child.find("/zero") is None

    def test_none_key(self):
        """ Handle None keys """
        with pytest.raises(utils.FormatError):
            tree = Tree({None: "weird key"})

    def test_deep_hierarchy(self):
        """ Deep hierarchy on one line """
        deep = Tree(EXAMPLES + "deep")
        assert len(deep.children) == 1

    def test_deep_dictionary(self):
        """ Get value from a deep dictionary """
        deep = Tree(EXAMPLES + "deep")
        assert deep.data['hardware']['memory']['size'] == 8
        assert deep.get(['hardware', 'memory', 'size']) == 8
        assert deep.get(['hardware', 'bad', 'size'], 12) == 12
        assert deep.get('nonexistent', default=3) == 3

    def test_merge_plus(self):
        """ Extending attributes using the '+' suffix """
        child = self.merge.find('/parent/extended')
        assert('General' in child.data['description'])
        assert('Specific' in child.data['description'])
        assert(child.data['tags'] == ['Tier1', 'Tier2', 'Tier3'])
        assert(child.data['time'] == 15)
        assert(child.data['vars'] == dict(x=1, y=2, z=3))
        assert(child.data['disabled'] == True)
        assert('time+' not in child.data)
        with pytest.raises(utils.MergeError):
            child.data["time+"] = "string"
            child.inherit()

    def test_merge_minus(self):
        """ Reducing attributes using the '-' suffix """
        child = self.merge.find('/parent/reduced')
        assert('General' in child.data['description'])
        assert('description' not in child.data['description'])
        assert(child.data['tags'] == ['Tier1'])
        assert(child.data['time'] == 5)
        assert(child.data['vars'] == dict(x=1, y=2))
        assert('time+' not in child.data)
        with pytest.raises(utils.MergeError):
            child.data["disabled-"] = True
            child.inherit()
        child.data.pop('disabled-')
        with pytest.raises(utils.MergeError):
            child.data["time-"] = "bad"
            child.inherit()

    def test_get(self):
        """ Get attributes """
        assert(isinstance(self.wget.get(), dict))
        assert('Petr' in self.wget.get('tester'))

    def test_show(self):
        """ Show metadata """
        assert(isinstance(self.wget.show(brief=True), type("")))
        assert(self.wget.show(brief=True).endswith("\n"))
        assert(isinstance(self.wget.show(), type("")))
        assert(self.wget.show().endswith("\n"))
        assert('tester' in self.wget.show())

    def test_update(self):
        """ Update data """
        data = self.wget.get()
        self.wget.update(None)
        assert(self.wget.data == data)

    def test_find_node(self):
        """ Find node by name """
        assert(self.wget.find("non-existent") == None)
        protocols = self.wget.find('/protocols')
        assert(isinstance(protocols, Tree))

    def test_find_root(self):
        """ Find metadata tree root """
        tree = Tree(os.path.join(EXAMPLES, "wget", "protocols"))
        assert(tree.find("/download/test"))

    def test_yaml_syntax_errors(self):
        """ Handle YAML syntax errors """
        path = tempfile.mkdtemp()
        fmf.cli.main("fmf init", path)
        with open(os.path.join(path, "main.fmf"), "w") as main:
            main.write("missing\ncolon:")
        with pytest.raises(utils.FileError):
            tree = fmf.Tree(path)
        rmtree(path)

    def test_inaccessible_directories(self):
        """ Inaccessible directories should be silently ignored """
        directory = tempfile.mkdtemp()
        accessible = os.path.join(directory, 'accessible')
        inaccessible = os.path.join(directory, 'inaccessible')
        os.mkdir(accessible, 511)
        os.mkdir(inaccessible, 000)
        with open(os.path.join(accessible, 'main.fmf'), 'w') as main:
            main.write('key: value\n')
        Tree.init(directory)
        tree = Tree(directory)
        assert tree.find('/accessible').get('key') == 'value'
        assert tree.find('/inaccessible') is None
        os.chmod(inaccessible, 511)
        rmtree(directory)

class TestRemote(object):
    """ e2e getting testcase data using remote reference """
    def test_get_remote_id(self):
        remote_id = {
            'url': 'https://github.com/psss/fmf.git',
            'ref': '0.10',
            'path': 'examples/deep',
            'name': '/one/two/three'
        }
        # Values of test in 0.10 tag
        expected_data = {'hardware': {'memory': {'size': 8}, 'network': {'model': 'e1000'}}, 'key': 'value'}
        node = Tree.node(remote_id)
        assert (node.get() == expected_data)

        with pytest.raises(utils.FilterError):
            remote_id['name'] = 'not_existing_name_'
            node = Tree.node(remote_id)
