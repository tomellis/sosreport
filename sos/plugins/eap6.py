import os
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

    optionList = [("home",  'JBoss\'s installation dir (i.e. JBOSS_HOME)', '', False),
                  ("javahome",  'Java\'s installation dir (i.e. JAVA_HOME)', '', False),
                  ("user",  'JBoss JMX invoker user to be used with twiddle.', '', False),
                  ("pass",  'JBoss JMX invoker user\'s password to be used with twiddle.', '', False),
                  ("logsize", 'max size (MiB) to collect per log file', '', 15),
                  ("stdjar",  'Collect jar statistics for standard jars.', '', True),
                  ("servjar",  'Collect jar statistics from any server configuration dirs.', '', True),
                  ("twiddle",  'Collect twiddle data.', '', True),
                  ("appxml",  'comma separated list of application\'s whose XML descriptors you want. The keyword \"all\" will collect all descriptors in the designated profile(s).', '', False)]

    __MD5_CHUNK_SIZE=128
    __jbossHome=None
    __haveJava=False
    __twiddleCmd=None
    __jbossSystemJarDirs = [ "client", "lib" , "common/lib" ]
    __jbossServerConfigDirs = ["standalone", "domain"]
    __jbossHTMLBody=None

    def __alert(self, msg):
        print msg
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

    def __getJavaHome(self):
        """
        This SOS plug-in makes extensive use of JBoss' twiddle program and twiddle uses Java.  As such, we
        need to ensure that java and JAVA_HOME is known to the plug-in so that it can use Java.
        This function will put JAVA_HOME and JAVA_HOME/bin into the environment if they're not already
        there.
        """
        javaHome=None
        java="bin/java"

        if self.getOption("javahome"):
            ## Prefer this value first over the ENV
            javaHome=self.getOption("javahome")
            self.addAlert("INFO: The Java installation directory supplied to SOS is " +
                          javaHome)
        elif os.environ.get("JAVA_HOME"):
            javaHome=os.environ.get("JAVA_HOME")
            self.addAlert("INFO: The Java installation directory (i.e. JAVA_HOME) from the environment is " +
                          javaHome)
        else:
            ## Test to see if Java is already in the PATH
            status = self.checkExtProg("java -version")
            if status:
                self.addAlert("INFO: The Java installation directory is in the system path.")
            else:
                self.addAlert("ERROR: The Java installation directory was not supplied.\
                The JBoss SOS plug-in will not collect twiddle data.")

            return status


        java=os.path.join(javaHome, java)
        if os.path.exists(java) and os.access(java, os.X_OK):
            os.environ['JAVA_HOME']=javaHome
            ## Place the supplied Java at the *head* of the path.
            os.environ['PATH'] = os.path.join(javaHome, "bin") + os.pathsep + os.environ['PATH']
            return True
        else:
            self.__alert("ERROR: The path to the Java installation directory does not exist.  Path is: %s" % (javaHome))
            return False


    def __getJMXCredentials(self):
        """
        Read the JMX credentials from the option list.
        Returns:
            A formatted credential string for twiddle consumption if both user and pass
            are supplied.  None otherwise.
        """
        credential = None
        ## Let's make a best effort not to pass expansions or escapes to the shell
        ## by strong quoting the user's input
        if self.getOption("user"):
            credential=" -u '" + self.getOption("user") + "' "
            if self.getOption("pass"):
                credential+=" -p '" + self.getOption("pass") + "' "
            else:
                credential=None
        return credential

    def __updateServerConfigDirs(self):
        """
        By default this plug-in will attempt to collect logs from every
        JBoss server configuration directory (i.e. profile).  The
        user may have supplied a limited list, as such, we must respect
        that wish.
        Returns:
            Nothing.  Will update __jbossServerConfigDirs if the user
            supplied a limited list.
        """
        if self.getOption("profile"):
            self.__jbossServerConfigDirs = self.getOptionAsList("profile")

    def __createHTMLBodyStart(self):
        """
        The free-form HTML that can be inserted into the SOS report with addCustomText is within
        a <p> block.  We need to add a few pieces of HTML so that all of our subsequent data will
        be rendered properly.
        """
        self.__jbossHTMLBody = """
       <br/>
       <br/>
        <script type="text/javascript">
        <!--
        function show(h) {
          var tbl = document.getElementById(h);
          tbl.style.display = 'block';
        }
        function hide(h) {
              var tbl = document.getElementById(h);
              tbl.style.display = 'none';
            }
        // -->
        </script>
        <b>JBoss SOS Report Table of Contents</b>
    <ul style="list-style-type: square">
        <li><a href="#system-jar-info">JBoss System Jar Information</a>
        </li>
        <li><a href="#profile-jar-info">JBoss Server Configurations Jar Information</a>
        </li>
        <li><a href="#jboss-home-directory-tree">JBOSS_HOME Directory Tree</a>
        </li>
        <li><a href="#jboss-system-mbean-data">JBoss JMX MBean Data from <tt>jboss.system:*</tt></a>
        </li>
        <li><a href="#jboss-mbean-data">JBoss JMX MBean Data from <tt>jboss:*</tt></a>
        </li>
        <li><a href="#jboss-mbean-summary">JBoss MBean Summary</a>
        </li>
        <li><a href="#jboss-messaging">JBoss JMX Messaging MBean Data from  <tt>jboss.messaging:*</tt></a>
        </li>
        <li><a href="#jboss-j2ee">JBoss JMX J2EE MBean Data from <tt>jboss.j2ee:*</tt></a>
        </li>
        <li><a href="#jboss-vfs">JBoss JMX VFS MBean Data from <tt>jboss.vfs:*</tt></a>
        </li>
        <li><a href="#jboss-jsr77-data">JBoss JSR77 Data</a>
        </li>
    </ul>
    <br/>
    <br/>
        """

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

        self.__jbossHTMLBody += """
    <div id="system-jar-info" style="font-weight: bold;">&ndash; JBoss System Jar Information</div>
        """

        for dir in self.__jbossSystemJarDirs:
            path=os.path.join(self.__jbossHome, dir)
            if os.path.exists(path):
                nicePath=path.replace(os.sep, "-")
                self.__jbossHTMLBody += """
    <div>
        &mdash; Summary of Jar Files in JBoss System Directory
        <tt>%s</tt>
        ( <a href="javascript:show('%s')">Show</a> / <a
            href="javascript:hide('%s')">Hide</a> ):
    </div>
    <div id="%s" style="overflow: hidden; display: none">
        <ul style="list-style-type: square">
                """ % (path,nicePath,nicePath,nicePath)

                found= False
                for jarFile in find("*.jar", path):
                    found= True
                    nicePath=jarFile.replace(os.sep, "-")
                    self.__jbossHTMLBody += """
                <li>Jar File: <tt>%s</tt><br/>
                    MD5: <tt>%s</tt>
                    <br /> Manifest File (
                    <a href="javascript:show('%s')">Show</a> /
                    <a href="javascript:hide('%s')">Hide</a> ):<br />
                    <div id="%s" style="overflow: hidden; display: none">
                        <pre>
                        %s
                        </pre>
                    </div>
                </li>
                            """ % (jarFile,
                                   self.__getMd5(jarFile),
                                   nicePath,
                                   nicePath,
                                   nicePath,
                                   self.__getManifest(jarFile))

                if not found:
                    self.addAlert("WARN: No jars found in JBoss system path (" + path + ").")
                self.__jbossHTMLBody += """
             </ul>
        </div>
                    """
            else:
                self.addAlert("ERROR: JBoss system path (" + path + ") does not exist.")
        return

    def __getServerConfigJarInfo(self, configDirAry):

        self.__jbossHTMLBody += """
    <br/>
    <br/>
    <div id="profile-jar-info" style="font-weight: bold;">&ndash; JBoss Server Configurations Jar Information</div>
        """
        for dir in configDirAry:
            serverDir = os.path.join("server", dir)
            path=os.path.join(self.__jbossHome, serverDir)
            if os.path.exists(path):
                nicePath=path.replace(os.sep, "-")
                self.__jbossHTMLBody += """
    <div>
        &mdash; Summary of Jar Files in the <tt>%s</tt> JBoss Server Configuration
        ( <a href="javascript:show('%s')">Show</a> / <a
            href="javascript:hide('%s')">Hide</a> ):
    </div>
    <div id="%s" style="overflow: hidden; display: none">
        <ul style="list-style-type: square">
                """ % (dir, nicePath,nicePath,nicePath)

                found = False
                for jarFile in find("*.jar", path):
                    found = True
                    nicePath=jarFile.replace(os.sep, "-")
                    self.__jbossHTMLBody += """
        <li id="system-jar-info">Jar File: <tt>%s</tt><br/>
            MD5: <tt>%s</tt>
            <br /> Manifest File (
            <a href="javascript:show('%s')">Show</a> /
            <a href="javascript:hide('%s')">Hide</a> ):<br />
            <div id="%s" style="overflow: hidden; display: none">
                <pre>
                %s
                </pre>
            </div>
        </li>
                    """ % (jarFile,
                           self.__getMd5(jarFile),
                           nicePath,
                           nicePath,
                           nicePath,
                           self.__getManifest(jarFile))

                if not found:
                    self.addAlert("WARN: No jars found in the JBoss server configuration (%s)." % (path))

                self.__jbossHTMLBody += """
     </ul>
</div>
            """
            else:
                self.addAlert("ERROR: JBoss server configuration path (" + path + ") does not exist.")

        return

    def query_api(self, url, postdata=None):
        try:
            import json
        except ImportError:
            import simplejson as json

        req = urllib2.Request("http://localhost:9990/management" + url, data=postdata)
        resp = urllib2.urlopen(req)
        return json.dumps(resp.read())


    def get_online_data(self):
        """
        This function co-locates calls to the management api that gather
        information from a running system.
        """

        self.addStringAsFile(
                self.query_api("/core-service/platform-mbean/type/runtime"),
                filename="runtime.txt")


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

        self.get_online_data()

        ## Check to see if the user passed in a limited list of server config jars.
#        self.__updateServerConfigDirs()

        ## Generate HTML Body for report
#        self.__createHTMLBodyStart()

        ## Generate hashes of the stock Jar files for the report.
#        if self.getOption("stdjar"):
#            self.__getStdJarInfo()

        ## Generate hashes for the Jars in the various profiles
#        if self.getOption("servjar"):
#            self.__getServerConfigJarInfo(self.__jbossServerConfigDirs)

        ## Generate a Tree for JBOSS_HOME
        tree = DirTree(self.__jbossHome).as_string()
        self.addStringAsFile(tree, "jboss_home_tree.txt")

#        if self.getOption("twiddle"):
            ## We need to know where Java is installed or at least ensure that it
            ## is available to the plug-in so that we can run twiddle.
#            self.__haveJava = self.__getJavaHome()
#            self.__buildTwiddleCmd()
#            self.__getTwiddleData()


#        self.addCustomText(self.__jbossHTMLBody)

        self.__getFiles(self.__jbossServerConfigDirs)

    def postproc(self):
        """
        Obfuscate passwords.
        """

#        for dir in self.__jbossServerConfigDirs:
#            path=os.path.join(self.__jbossHome, "server", dir)

#            self.doRegexSub(os.path.join(path,"conf","login-config.xml"),
#                            re.compile(r'"password".*>.*</module-option>', re.IGNORECASE),
#                            r'"password">********</module-option>')

#            tmp = os.path.join(path,"conf", "props")
#            for propFile in find("*-users.properties", tmp):
#                self.doRegexSub(propFile,
#                                r"=(.*)",
#                                r'=********')

            # Remove PW from -ds.xml files
#            tmp=os.path.join(path, "deploy")
#            for dsFile in find("*-ds.xml", tmp):
#                self.doRegexSub(dsFile,
#                                re.compile(r"<password.*>.*</password.*>", re.IGNORECASE),
#                                r"<password>********</password>")
