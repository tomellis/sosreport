import subprocess

from sos.policies import PackageManager, Policy
from sos.plugins import IndependentPlugin

class OSXPolicy(Policy):

    def __init__(self):
        self._parse_uname()
        self.ticketNumber = None
        self.reportName = self.hostname
        self.package_manager = PackageManager()

    @classmethod
    def check(class_):
        try:
            p = subprocess.Popen("sw_vers", shell=True, stdout=subprocess.PIPE)
            ver_string = p.communicate()[0]
            return "Mac OS X" in ver_string
        except Exception, e:
            return False
