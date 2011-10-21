import os

from sos.policies import PackageManager, Policy
from sos.plugins import IndependentPlugin
import subprocess

class WindowsPolicy(Policy):

    def __init__(self):
        pass

    def setCommons(self, commons):
        self.commons = commons

    def validatePlugin(self, plugin_class):
        return issubclass(plugin_class, IndependentPlugin)

    @classmethod
    def check(class_):
        try:
            p = subprocess.Popen("ver", shell=True, stdout=subprocess.PIPE)
            return "Windows" in p.communicate()[0]
        except:
            return False

    def preferedArchive(self):
        from sos.utilities import ZipFileArchive
        return ZipFileArchive

    def pkgByName(self, name):
        return None

    def preWork(self):
        pass

    def packageResults(self, archive_filename):
        self.report_file = archive_filename

    def getArchiveName(self):
        if self.ticketNumber:
            self.reportName += "." + self.ticketNumber
        return "sosreport-%s-%s" % (self.reportName, time.strftime("%Y%m%d%H%M%S"))

    def displayResults(self, final_filename=None):

        if not final_filename:
            return False

        fp = open(final_filename, "r")
        md5sum = md5(fp.read()).hexdigest()
        fp.close()

        fp = open(final_filename + ".md5", "w")
        fp.write(md5sum + "\n")
        fp.close()

    def uploadResults(self, final_filename=None):
        pass
