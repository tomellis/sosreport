#!/usr/bin/env python

import unittest
import os
import tarfile
import zipfile

from sos.utilities import TarFileArchive, ZipFileArchive

class ZipFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.zf = ZipFileArchive('test')

    def tearDown(self):
        os.unlink('test.zip')

    def check_for_file(self, filename):
        zf = zipfile.ZipFile('test.zip', 'r')
        zf.getinfo(filename)
        zf.close()

    def test_create(self):
        self.zf.close()

    def test_add_file(self):
        self.zf.add_file('tests/worker.py')
        self.zf.close()

        self.check_for_file('test/tests/worker.py')

    def test_add_dir(self):
        self.zf.add_file('tests/')
        self.zf.close()

        self.check_for_file('test/tests/worker.py')

    def test_add_renamed(self):
        self.zf.add_file('tests/worker.py', dest='tests/worker_renamed.py')
        self.zf.close()

        self.check_for_file('test/tests/worker_renamed.py')

    def test_add_renamed_dir(self):
        self.zf.add_file('tests/', 'tests_renamed/')
        self.zf.close()

        self.check_for_file('test/tests_renamed/worker.py')

    def test_add_string(self):
        self.zf.add_string('this is content', 'tests/string_test.txt')
        self.zf.close()

        self.check_for_file('test/tests/string_test.txt')

class TarFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.tf = TarFileArchive('test')

    def tearDown(self):
        os.unlink('test.tar')

    def check_for_file(self, filename):
        rtf = tarfile.open('test.tar')
        rtf.getmember(filename)
        rtf.close()

    def test_create(self):
        self.tf.close()
        self.assertTrue(os.path.exists('test.tar'))

    def test_add_file(self):
        self.tf.add_file('tests/worker.py')
        self.tf.close()

        self.check_for_file('test/tests/worker.py')

    def test_add_dir(self):
        self.tf.add_file('tests/')
        self.tf.close()

        self.check_for_file('test/tests/worker.py')

    def test_add_renamed(self):
        self.tf.add_file('tests/worker.py', dest='tests/worker_renamed.py')
        self.tf.close()

        self.check_for_file('test/tests/worker_renamed.py')

    def test_add_renamed_dir(self):
        self.tf.add_file('tests/', 'tests_renamed/')
        self.tf.close()

        self.check_for_file('test/tests_renamed/worker.py')

    def test_add_string(self):
        self.tf.add_string('this is content', 'tests/string_test.txt')
        self.tf.close()

        self.check_for_file('test/tests/string_test.txt')

if __name__ == "__main__":
    unittest.main()
