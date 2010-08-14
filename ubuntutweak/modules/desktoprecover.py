# Ubuntu Tweak - magic tool to configure Ubuntu
#
# Copyright (C) 2010 TualatriX <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import gtk
import glob
import gobject
import logging

from subprocess import Popen, PIPE

from ubuntutweak.utils import icon
from ubuntutweak.common.consts import CONFIG_ROOT
from ubuntutweak.common.gui import GuiWorker
from ubuntutweak.modules  import TweakModule

log = logging.getLogger('DesktopRecover')

class CateView(gtk.TreeView):
    (COLUMN_ICON,
     COLUMN_DIR,
     COLUMN_TITLE
    ) = range(3)

    path_dict = {
        '/apps': _('Applications'),
        '/desktop': _('Desktop'),
        '/system': _('System'),
    }

    def __init__(self):
        gtk.TreeView.__init__(self)

        self.set_rules_hint(True)
        self.model = self.__create_model()
        self.set_model(self.model)
        self.__add_columns()
        self.update_model()

        selection = self.get_selection()
        selection.select_iter(self.model.get_iter_first())

    def __create_model(self):
        '''The model is icon, title and the list reference'''
        model = gtk.ListStore(
                    gtk.gdk.Pixbuf,
                    gobject.TYPE_STRING,
                    gobject.TYPE_STRING)

        return model

    def __add_columns(self):
        column = gtk.TreeViewColumn(_('Categories'))

        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.set_attributes(renderer, pixbuf=self.COLUMN_ICON)

        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.set_sort_column_id(self.COLUMN_TITLE)
        column.set_attributes(renderer, text=self.COLUMN_TITLE)

        self.append_column(column)

    def update_model(self):
        for path, title in self.path_dict.items():
            pixbuf = icon.get_from_name('ubuntu-tweak', size=24)
            iter = self.model.append(None)
            self.model.set(iter,
                           self.COLUMN_ICON, pixbuf,
                           self.COLUMN_DIR, path,
                           self.COLUMN_TITLE, title)

class KeyDirView(gtk.TreeView):
    (COLUMN_ICON,
     COLUMN_DIR,
     COLUMN_TITLE
    ) = range(3)

    def __init__(self):
        gtk.TreeView.__init__(self)

        self.model = self.__create_model()
        self.set_model(self.model)
        self.__add_columns()

    def __create_model(self):
        ''' The first is for icon, second is for real path, second is for title (if availabel)'''
        model = gtk.ListStore(gtk.gdk.Pixbuf,
                              gobject.TYPE_STRING,
                              gobject.TYPE_STRING)

        return model

    def __add_columns(self):
        column = gtk.TreeViewColumn(_('KeyDir'))

        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.set_attributes(renderer, pixbuf=self.COLUMN_ICON)

        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.set_sort_column_id(self.COLUMN_TITLE)
        column.set_attributes(renderer, text=self.COLUMN_TITLE)

        self.append_column(column)

    def update_model(self, dir):
        self.model.clear()
        
        process = Popen(['gconftool-2', '--all-dirs', dir], stdout=PIPE)
        stdout, sterror = process.communicate()
        if sterror:
            log.error(sterror)
            #TODO raise error or others
            return

        dirlist = stdout.split()
        dirlist.sort()
        for dir in dirlist:
            title = dir.split('/')[-1]

            pixbuf = icon.get_from_name(title, size=24)
            iter = self.model.append(None)
            self.model.set(iter,
                           self.COLUMN_ICON, pixbuf,
                           self.COLUMN_DIR, dir,
                           self.COLUMN_TITLE, title)

class DesktopRecover(TweakModule):
    __title__ = _('Desktop Recover')
    __desc__ = _('Backup and recover your desktop and applications setting easily')
    __icon__ = 'gconf-editor'
    __category__ = 'system'

    def __init__(self):
        TweakModule.__init__(self)

        self.guiworker = GuiWorker('desktoprecover.ui')
        self.setup_backup_model()

        hbox = gtk.HBox(False, 5)
        self.add_start(hbox)

        self.cateview = CateView()
        self.cate_selection = self.cateview.get_selection()
        self.cate_selection.connect('changed', self.on_cateview_changed)
        hbox.pack_start(self.cateview, False, False, 0)

        vpaned = gtk.VPaned()
        hbox.pack_start(vpaned)

        self.keydirview = KeyDirView()
        self.keydir_selection = self.keydirview.get_selection()
        self.keydir_selection.connect('changed', self.on_keydirview_changed)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self.keydirview)
        vpaned.pack1(sw, True, False)

        self.guiworker.window1.remove(self.guiworker.recover_box)
        vpaned.pack2(self.guiworker.recover_box, False, False)

        self.on_cateview_changed(self.cate_selection)
        self.show_all()

    def setup_backup_model(self):
        model = gtk.ListStore(gobject.TYPE_STRING,
                              gobject.TYPE_STRING)
        backup_combobox = self.guiworker.backup_combobox

        backup_combobox.set_model(model)

        cell = gtk.CellRendererText()
        backup_combobox.pack_start(cell, True)
        backup_combobox.add_attribute(cell, 'text', 0)

    def update_backup_model(self, dir):
        backup_combobox = self.guiworker.backup_combobox
        model = backup_combobox.get_model()
        model.clear()

        dirs = dir.split('/')
        if len(dirs) == 2:
            name_pattern = os.path.join(CONFIG_ROOT, 'desktoprecover', dirs[1])
        else:
            name_pattern = os.path.join(CONFIG_ROOT, 'desktoprecover', dirs[1], dirs[2])

        log.debug('Use glob to find the name_pattern: %s' % name_pattern)
        file_lsit = glob.glob(name_pattern + '*.xml')
        if file_lsit:
            for file in glob.glob(name_pattern + '*.xml'):
                iter = model.append(None)
                model.set(iter, 0, file, 1, file)
                backup_combobox.set_active_iter(iter)
            self.guiworker.delete_button.set_sensitive(True)
        else:
            iter = model.append(None)
            model.set(iter, 0, _('No Backup yet'), 1, '')
            backup_combobox.set_active_iter(iter)
            self.guiworker.delete_button.set_sensitive(False)

    def on_cateview_changed(self, widget):
        model, iter = widget.get_selected()
        if iter:
            dir = model.get_value(iter, self.cateview.COLUMN_DIR)
            self.keydirview.update_model(dir)

            self.guiworker.dir_label.set_text(dir)
            self.update_backup_model(dir)

    def on_keydirview_changed(self, widget):
        model, rows = widget.get_selected_rows()
        if len(rows) > 2:
            pass
        elif len(rows) == 1:
            model, iter = widget.get_selected()

            dir = model.get_value(iter, self.keydirview.COLUMN_DIR)
            self.guiworker.dir_label.set_text(dir)
        else:
            pass
