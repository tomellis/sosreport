## Copyright (C) 2012 Eucalyptus Systems, Inc., Tom Ellis <tellis@eucalyptus.com>

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

import os
from sos.plugins import Plugin, RedHatPlugin

class eucalyptus(Plugin):
    """Eucalyptus Cloud related information
    """
    plugin_name = "eucalyptus"

    optionList = [("log", "gathers eucalyptus logs", "slow", False)]

    packages = ('eucalyptus',
                'eucalyptus-cc',
                'eucalyptus-sc',
                'eucalyptus-walrus',
                'eucalyptus-nc')

    def setup(self):
        # All Eucalyptus components
        self.addCopySpecs(["/etc/eucalyptus/",
                           "/var/log/eucalyptus/"])
