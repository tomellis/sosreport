#!/usr/bin/env python

import unittest
import os

from sos.reporting import Report, Section, Block, List, Error

class ReportTest(unittest.TestCase):

    def test_empty(self):
        report = Report()

        self.assertEquals("<report />", str(report))

    def test_named(self):
        report = Report(name="sosreport")

        self.assertEquals('<report name="sosreport" />', str(report))

    def test_nested_section(self):
        report = Report(name="parent")
        section = Section(name="section")
        report.add(section)

        self.assertEquals('<report name="parent"><section name="section" /></report>',
                str(report))

    def test_cannot_nest_reports(self):
        report1 = Report(name="first")
        report2 = Report(name="second")

        try:
            report1.add(report2)
            self.fail("Was allowed to nest two report objects.")
        except Error:
            pass

    def test_deeply_nested(self):
        report = Report()
        section = Section()
        block = Block()

        section.add(block)
        report.add(section)

        self.assertEquals('<report><section><block /></section></report>', str(report))

class SectionTest(unittest.TestCase):

    def test_empty(self):
        section = Section()

        self.assertEquals("<section />", str(section))

    def test_named(self):
        section = Section(name="test")

        self.assertEquals('<section name="test" />', str(section))

    def test_cannot_add_a_report(self):
        section = Section(name="test")
        report = Report(name="test")

        try:
            section.add(report)
            self.fail("Was allowed to nest a report in a section.")
        except Error:
            pass

class ListTest(unittest.TestCase):

    def test_add_item(self):
        list_ = List(name="test")
        list_.add_item("an item")

        self.assertEquals('<list name="test"><item>an item</item></list>', str(list_))

    def test_add_item_with_href(self):
        list_ = List(name="test")
        list_.add_item("an item", href="path/to/an/item")

        self.assertEquals(
                '<list name="test"><item href="path/to/an/item">an item</item></list>',
                str(list_))

    def test_add_real_list(self):
        list_ = List(name="test", content=['an item', 'another item'])

        self.assertEquals(
                '<list name="test"><item>an item</item><item>another item</item></list>',
                str(list_))


if __name__ == "__main__":
    unittest.main()
