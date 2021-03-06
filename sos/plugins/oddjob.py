## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class oddjob(Plugin, RedHatPlugin):
    """oddjob related information
    """

    files = ('/etc/oddjobd.conf',)
    packages = ('oddjob',)

    def setup(self):
        self.addCopySpec("/etc/oddjobd.conf")
        self.addCopySpec("/etc/oddjobd.conf.d")
        self.addCopySpec("/etc/dbus-1/system.d/oddjob.conf")
