import os
import re
import zipfile
import platform
import fnmatch
import shlex
import subprocess
import string
import grp, pwd
import urllib2

from sos.plugins import Plugin, IndependentPlugin
from sos.utilities import DirTree, find, md5sum

class EAP6(Plugin, IndependentPlugin):
    """JBoss related information
    """

    requires_root = False

    version = "1.0"

    optionList = [
          ("home",  "JBoss's installation dir (i.e. JBOSS_HOME)", '', False),
          ("logsize", 'max size (MiB) to collect per log file', '', 15),
          ("stdjar",  'Collect jar statistics for standard jars.', '', True),
          ("address", 'hostname:port of the management api for jboss', '', 'localhost:9990'),
          ("user", 'username for management console', '', None),
          ("pass", 'password for management console', '', None),
          ("appxml",  "comma separated list of application's whose XML descriptors you want. The keyword 'all' will collect all descriptors in the designated profile(s).", '', False),
    ]

    __MD5_CHUNK_SIZE=128
    __jbossHome=None
    __haveJava=False
    __twiddleCmd=None
    __jbossServerConfigDirs = ["standalone", "domain"]
    __jbossHTMLBody=None

    def __alert(self, msg):
        self.soslog.error(msg)
        self.addAlert(msg)

    def __getJbossHome(self):
        """
        Will attempt to locate the JBoss installation dir in either jboss.home or
        scrape it from the environment variable JBOSS_HOME.
        Returns:
            True JBOSS_HOME is set and the path exists.  False otherwise.
        """

        if self.getOption("home"):
            ## Prefer this value first over the ENV
            self.__jbossHome=self.getOption("home")
            self.addAlert("INFO: The JBoss installation directory supplied to SOS is " +
                          self.__jbossHome)
        elif os.environ.get("JBOSS_HOME"):
            self.__jbossHome=os.environ.get("JBOSS_HOME")
            self.addAlert("INFO: The JBoss installation directory (i.e. JBOSS_HOME) from the environment is " +
                          self.__jbossHome)
        else:
            self.addAlert("ERROR: The JBoss installation directory was not supplied.\
              The JBoss SOS plug-in cannot continue.")
            return False

        return True

    def __getMd5(self, file):
        """Returns the MD5 sum of the specified file."""

        retVal = "?" * 32

        try:
            retVal = md5sum(file, self.__MD5_CHUNK_SIZE)
        except IOError, ioe:
            self.__alert("ERROR: Unable to open %s for reading.  Error: %s" % (file,ioe))

        return retVal

    def __getManifest(self, jarFile):
        """
        Given a jar file, this function will extract the Manifest and return it's contents
        as a string.
        """
        manifest = None
        try:
            zf = zipfile.ZipFile(jarFile)
            try:
                manifest = zf.read("META-INF/MANIFEST.MF")
            except Exception, e:
                self.__alert("ERROR: reading manifest from %s.  Error: %s" % (jarFile, e))
            zf.close()
        except Exception, e:
                self.__alert("ERROR: reading contents of %s.  Error: %s" % (jarFile, e))
        return manifest

    def __getStdJarInfo(self):
        found = False
        jar_info_list = []
        for jarFile in find("*.jar", self.__jbossHome):
            checksum = self.__getMd5(jarFile)
            manifest = self.__getManifest(jarFile)
            path = jarFile.replace(self.__jbossHome, 'JBOSSHOME')
            if manifest:
                manifest = manifest.strip()
            jar_info_list.append((path, checksum, manifest))
            found = True
        if found:
            jar_info_list.sort()
            self.addStringAsFile("\n".join([
                "%s\n%s\n%s\n" % (name, checksum, manifest)
                for (name, checksum, manifest) in jar_info_list]),
                'jarinfo.txt')
        else:
            self.addAlert("WARN: No jars found in JBoss system path (" + path + ").")

    def query_api(self, url):
        try:
            return self.query_java(url)
        except Exception, e:
            return self.query_http(url)

    def query_java(self, url):
        try:
            raise Exception
        except Exception, e:
            pass
            # throw exception to do http stuff

    def query_http(self, url, postdata=None):
        try:
            import json
        except ImportError:
            import simplejson as json

        host_port = self.getOption('address')
        username = self.getOption('user')
        password = self.getOption('pass')
        uri = "http://" + host_port + "/management" + url

        opener = urllib2.build_opener()

        if username and password:
            params = {"realm": "PropertiesMgmtSecurityRealm",
                    "uri": uri,
                    "user": username,
                    "passwd": password}

            digest_auth_handler = urllib2.HTTPDigestAuthHandler()
            digest_auth_handler.add_password(**params)

            basic_auth_handler = urllib2.HTTPBasicAuthHandler()
            basic_auth_handler.add_password(**params)

            opener.add_handler(digest_auth_handler)
            opener.add_handler(basic_auth_handler)

        req = urllib2.Request(uri, data=postdata)

        try:
            resp = opener.open(req)
            return json.loads(resp.read())
        except Exception, e:
            self.addAlert("Could not query url: %s; error: %s" % (uri, e))


    def get_online_data(self):
        """
        This function co-locates calls to the management api that gather
        information from a running system.
        """
        import pprint

        for url, outfile in [
                ("/core-service/platform-mbean/type/runtime", "runtime.txt"),
                ]:
            self.addStringAsFile(pprint.pformat(self.query_api(url)), filename=outfile)


    def __getFiles(self, configDirAry):
        """
        This function will collect files from JBOSS_HOME for analysis.  The scope of files to
        be collected are determined by options to this SOS plug-in.
        """

        for dir_ in configDirAry:
            path = os.path.join(self.__jbossHome, dir_)
            ## First add forbidden files
            self.addForbiddenPath(os.path.join(path, "tmp"))
            self.addForbiddenPath(os.path.join(path, "work"))
            self.addForbiddenPath(os.path.join(path, "data"))

            if os.path.exists(path):
                ## First get everything in the conf dir
                confDir = os.path.join(path, "configuration")

                self.doCopyFileOrDir(confDir, sub=(self.__jbossHome, 'JBOSSHOME'))
                ## Log dir next
                logDir = os.path.join(path, "log")

                for logFile in find("*", logDir):
                    self.addCopySpecLimit(logFile,
                            self.getOption("logsize"),
                            sub=(self.__jbossHome, 'JBOSSHOME'))

                ## Deploy dir
                deployDir = os.path.join(path, "deployments")

                for deployFile in find("*", deployDir, max_depth=1):
                    self.addCopySpec(deployFile, sub=(self.__jbossHome, 'JBOSSHOME'))

    def setup(self):
        ## We need to know where JBoss is installed and if we can't find it we
        ## must exit immediately.
        if not self.__getJbossHome():
            self.exit_please()

        try:
            self.get_online_data()
        except urllib2.URLError:
            pass

        ## Generate hashes of the stock Jar files for the report.
        if self.getOption("stdjar"):
            self.__getStdJarInfo()

        ## Generate a Tree for JBOSS_HOME
        tree = DirTree(self.__jbossHome).as_string()
        self.addStringAsFile(tree, "jboss_home_tree.txt")

        self.__getFiles(self.__jbossServerConfigDirs)

    # FIXME: this is still not right, tweak the search paths to pick up the right files
    def postproc(self):
        """
        Obfuscate passwords.
        """

        for dir_ in self.__jbossServerConfigDirs:
            path = os.path.join(self.__jbossHome, dir_)

            self.doRegexSub(os.path.join(path,"configuration","login-config.xml"),
                            re.compile(r'"password".*>.*</module-option>', re.IGNORECASE),
                            r'"password">********</module-option>')

            tmp = os.path.join(path,"conf", "props")
            for propFile in find("*-users.properties", tmp):
                self.doRegexSub(propFile,
                                r"=(.*)",
                                r'=********')

#             Remove PW from -ds.xml files
            tmp = os.path.join(path, "deploy")
            for dsFile in find("*-ds.xml", tmp):
                self.doRegexSub(dsFile,
                                re.compile(r"<password.*>.*</password.*>", re.IGNORECASE),
                                r"<password>********</password>")
