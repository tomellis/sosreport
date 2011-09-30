from xml.etree import ElementTree

class Error(Exception):
    """Exception throw when any error occurs in the reporting framework"""
    pass

class ReportNode(object):

    ELEMENT_NAME = "node"

    def __init__(self, name=None, content=None):
        self.element = ElementTree.Element(self.ELEMENT_NAME)

        if name:
            self.element.attrib['name'] = name

        if content:
            self.add_content(content)

    def __str__(self):
        return ElementTree.tostring(self.element)

    def add(self, node):
        if self.can_add(node):
            self.element.append(node.element)
        else:
            raise Error("Adding this %s to %s is not allowed." % (
                node.element.attrib['name'],
                self.element.attrib['name'],))

    def add_content(self, content):
        for item in content:
            self.add(item)

    def can_add(self, node):
        return False


class Report(ReportNode):
    """The root element of a report. This is a container for sections."""

    ELEMENT_NAME = "report"

    def can_add(self, node):
        return not issubclass(node.__class__, self.__class__)


class Section(ReportNode):
    """A section is a container for leaf elements. Sections may be nested
    inside of Report objects only."""

    ELEMENT_NAME = "section"

    def can_add(self, node):
        return not issubclass(node.__class__, (Report, self.__class__))


class Block(ReportNode):

    ELEMENT_NAME = "block"


class List(ReportNode):

    ELEMENT_NAME = "list"

    def add_item(self, item, href=None):
        item_element = ElementTree.SubElement(self.element, 'item')
        item_element.text = item
        if href:
            item_element.attrib['href'] = href

    def add_content(self, content):
        for item in content:
            self.add_item(item)


class Pre(ReportNode):

    ELEMENT_NAME = "pre"
