"""
Wetland DEM Ponding Model version 2.0
Copyright (c) 2010, 2012, 2014, 2020 Kevin Shook, Centre for Hydrology
Developed by Oluwaseun Sharomi, Raymond Spiteri and Tonghe Liu
Numerical Simulation Laboratory, University of Saskatchewan.

--------------------------------------------------------------------
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

This program adds water to an ArcGIS ASCII file of water runoff
and redistributes water over the DEM
From the algorithm of Shapiro, M., & Westervelt, J. (1992).
An Algebra for GIS and Image Processing (pp. 1-22).
"""

import os
import platform
import string
import subprocess
import sys
import threading
import time

import wx

lock = threading.Lock()

if os.path.isfile('runoff.cl'):
    pass
else:
    raise AssertionError("runoff.cl not present. Exiting now")
if os.path.isfile('colormap_black.txt'):
    pass
else:
    raise AssertionError("colormap_black.txt not present. Exiting now")

platx = platform.system()


if platx in ('Darwin', 'Linux'):
    if os.path.isfile('cmap_black.sh'):
        pass
    else:
        raise AssertionError("cmap_black.sh not present. Exiting now")

    if os.path.isfile('WDPMCL'):
        pass
    else:
        raise AssertionError("WDPMCL not present. Exiting now")


class RedirectText:
    '''redirect text'''
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self,string):
        '''write'''
        wx.CallAfter(self.out.WriteText, string)

class CharValidator(wx.PyValidator):
    '''check if the char is validate'''
    def __init__(self,flag):
        wx.Validator.__init__(self)
        self.flag=flag
        self.Bind(wx.EVT_CHAR, self.on_char)

    def on_char(self, evt):
        '''on char'''
        key=chr(evt.GetKeyCode())
        if self.flag == "no-alpha" and key in string.ascii_letters:
            return
        if self.flag == "no-digit" and key in string.digits:
            return
        evt.Skip()

class Size(wx.Frame):
    '''main body'''
    def __init__(self, parent, id_):
        wx.Frame.__init__(self, parent, id_, 'Wetland DEM Ponding Model', size=(1300, 850),
                                  style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|
                                  wx.SYSTEM_MENU|wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN)
        self.panel = wx.ScrolledWindow(self, id_)
        x_p=35
        y_p=5

        ## Generate picture (text and button)
        self.lblname9xa = wx.StaticText(self.panel, label="Output to .PNG", pos=(10,25*x_p))
        self.txt9xa = wx.TextCtrl(self.panel, -1, pos=(round(8*x_p), round(25*x_p)),
                        size=(round(2.5*x_p), round(x_p-y_p)))
        self.button19xa = wx.Button(self.panel, -1, "Browse", pos=(round(10.5*x_p),round(25*x_p)),
                        size=(round(2.5*x_p), round(x_p-y_p)))
        self.button19xa.Bind(wx.EVT_BUTTON, self.on_open_dem)
        self.convert=wx.Button(self.panel, label="convert", pos=(round(13*x_p),round(25*x_p)),
                        size=(round(2.5*x_p), round(x_p-y_p)))
        self.convert.Bind(wx.EVT_BUTTON, self.bitmap_convert)
        self.txt9xa.Enable(False)
        self.button19xa.Enable(False)
        self.convert.Enable(False)

        ## Run the module (text and button)
        self.runbutton=wx.Button(self.panel, label="Start", pos=(round(10),round(24*x_p)),
                        size=(round(2.5*x_p), round(x_p-y_p)))
        self.clearbutton=wx.Button(self.panel, label="Clear",
        		pos=(8*x_p,24*x_p), size=(round(2.5*x_p), x_p-y_p))
        self.endbutton=wx.Button(self.panel, label="End", pos=(13*x_p,24*x_p),
        		size=(round(2.5*x_p), x_p-y_p))
        self.Bind(wx.EVT_BUTTON, self.run_sim, self.runbutton)
        self.Bind(wx.EVT_BUTTON, self.on_clear_screen, self.clearbutton)
        self.Bind(wx.EVT_BUTTON, self.on_abort_button, self.endbutton)
        self.runbutton.Enable(False)
        self.endbutton.Enable(False)
        self.Bind(wx.EVT_CLOSE,self.end_simulation)

        ## Menu (text and button)
        self.flagz = 0
        menubar = wx.MenuBar()
        filez = wx.Menu()
        quit = wx.MenuItem(filez, 1, '&Quit\tCtrl+Q')
        about = wx.MenuItem(filez, 3, '&About\tCtrl+A')
        filez.Append(quit)
        filez.Append(about)
        self.Bind(wx.EVT_MENU, self.on_quit, id=1)
        self.Bind(wx.EVT_MENU, self.on_about, id=3)
        menubar.Append(filez, '&File')
        self.SetMenuBar(menubar)
        self.Show(True)

        ## Working directory (text and button)
        self.lblname0a = wx.StaticText(self.panel, label="Working Directory:", pos=(10,x_p))
        self.txt0a = wx.TextCtrl(self.panel, -1, pos=(8*x_p, x_p), size=(5*x_p, x_p-y_p))
        self.button00a = wx.Button(self.panel, -1, "Browse", pos=(13*x_p,x_p),
        		size=(round(2.5*x_p), x_p-y_p))
        self.button00a.Bind(wx.EVT_BUTTON, self.on_open_0)

        ## Choose module (text and button)
        methods = [" ", "add", "subtract", "drain", "TextFile"]
        self.lblname0 = wx.StaticText(self.panel, label="Methods:", pos=(10,2*x_p))
        self.combo = wx.ComboBox(self.panel, -1, pos=(8*x_p, 2*x_p), size=(5*x_p, x_p-y_p),
                        choices=methods, style=wx.CB_READONLY)
        self.combo.Bind(wx.EVT_COMBOBOX, self.verify)
        self.combo.Enable(False)

        ## Set DEM, water, output and scratch files (text and button)
        self.lblname1 = wx.StaticText(self.panel, label="DEM File:", pos=(10,3*x_p))
        self.txt1 = wx.TextCtrl(self.panel, -1, pos=(8*x_p, 3*x_p), size=(5*x_p, x_p-y_p))
        self.button11 = wx.Button(self.panel, -1, "Browse",
        		pos=(13*x_p,3*x_p), size=(round(2.5*x_p), x_p-y_p))
        self.button11.Bind(wx.EVT_BUTTON, self.on_open_1)
        self.lblname2 = wx.StaticText(self.panel, label="Water File:", pos=(10,4*x_p))
        self.txt2 = wx.TextCtrl(self.panel, -1, pos=(8*x_p, 4*x_p),
        		size=(5*x_p, x_p-y_p),value='NULL')
        self.button12 = wx.Button(self.panel, -1, "Browse",
        		pos=(13*x_p,4*x_p), size=(round(2.5*x_p), x_p-y_p))
        self.button12.Bind(wx.EVT_BUTTON, self.on_open_2)
        self.lblname3 = wx.StaticText(self.panel, label="Output File:", pos=(10,5*x_p))
        self.txt3 = wx.TextCtrl(self.panel, -1, pos=(8*x_p, 5*x_p), size=(5*x_p, x_p-y_p),
        		value='water.asc')
        self.lblname4 = wx.StaticText(self.panel, label="Scratch File:", pos=(10,6*x_p))
        self.txt4 = wx.TextCtrl(self.panel, -1, pos=(8*x_p, 6*x_p),
        		size=(5*x_p, x_p-y_p),value='NULL')

        ## Add Components
        self.lblname50 = wx.StaticText(self.panel, label="Add Components", pos=(10,7*x_p))
        self.lblname5 = wx.StaticText(self.panel, label="Depth of water (mm):", pos=(10,8*x_p))
        self.editname5 = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,8*x_p),
        		value='10', validator=CharValidator("no-alpha"))
        self.lblname6 = wx.StaticText(self.panel, label="Water runoff fraction:", pos=(10,9*x_p))
        self.editname6 = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,9*x_p),value='1',
                        validator=CharValidator("no-alpha"))
        self.lblname7 = wx.StaticText(self.panel, label="Elevation tolerance (mm):",
        		pos=(10,10*x_p))
        self.editname7 = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,10*x_p),
        		value='1', validator=CharValidator("no-alpha"))

        ## Subtract Components
        self.lblname5a0 = wx.StaticText(self.panel, label="Subtract Components", pos=(10,11*x_p))
        self.lblname5a = wx.StaticText(self.panel, label="Depth of water (mm):", pos=(10,12*x_p))
        self.editname5a = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,12*x_p),
        		value='1', validator=CharValidator("no-alpha"))
        self.lblname7a = wx.StaticText(self.panel, label="Elevation tolerance (mm):",
        		pos=(10,13*x_p))
        self.editname7a = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p),
        		pos=(8*x_p,13*x_p), value='1', validator=CharValidator("no-alpha"))

        ## Drain Components
        self.lblname6b0 = wx.StaticText(self.panel, label="Drain Components", pos=(10,14*x_p))
        self.lblname6b = wx.StaticText(self.panel, label="Elevation tolerance (mm):",
        		pos=(10,15*x_p))
        self.editname6b = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,15*x_p),
        		value='1', validator=CharValidator("no-alpha"))
        self.lblname7b = wx.StaticText(self.panel, label="Drain tolerance (m3):", pos=(10,16*x_p))
        self.editname7b = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,16*x_p),
        		value='1', validator=CharValidator("no-alpha"))

        ## Other Components
        self.lblname6bz = wx.StaticText(self.panel, label="Computation Settings", pos=(10,17*x_p))
        methods1 = [" ", "Serial CPU", "OpenCL"]
        self.lblname8 = wx.StaticText(self.panel, label="Serial/OpenCL:", pos=(10,18*x_p))
        self.combo8 = wx.ComboBox(self.panel, -1, pos=(8*x_p, 18*x_p), size=(5*x_p, x_p-y_p),
                        choices=methods1, style=wx.CB_READONLY)
        self.button18 = wx.Button(self.panel, -1, "Process", pos=(13*x_p,18*x_p),
        		 size=(round(2.5*x_p), x_p-y_p))
        self.button18.Bind(wx.EVT_BUTTON, self.process)
        methods2 = [" ", "GPU", "CPU"]
        self.lblname9 = wx.StaticText(self.panel, label="OpenCL CPU/GPU:", pos=(10,19*x_p))
        self.combo9 = wx.ComboBox(self.panel, -1, pos=(8*x_p, 19*x_p), size=(5*x_p, x_p-y_p),
                                          choices=methods2, style=wx.CB_READONLY)

        ## water depth threshold component
        self.lblname10 = wx.StaticText(self.panel, label="Zero depth threshold value (mm):",
                        pos=(10,20*x_p))
        self.editname10 = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,20*x_p),
        		value='0', validator=CharValidator("no-alpha"))
        self.lblname11 = wx.StaticText(self.panel,
                         label="Iteration limitation (0 if no limitation):", pos=(10,21*x_p))
        self.editname11 = wx.TextCtrl(self.panel, size=(5*x_p, x_p-y_p), pos=(8*x_p,21*x_p),
        		value='0', validator=CharValidator("no-alpha"))

        ## Load variables from a file
        self.lblname9a0 = wx.StaticText(self.panel, label="Load from file", pos=(10,22*x_p))
        self.lblname9a = wx.StaticText(self.panel, label="Text File:", pos=(10,23*x_p))
        self.txt9a = wx.TextCtrl(self.panel, -1, pos=(8*x_p, 23*x_p), size=(5*x_p, x_p-y_p))
        self.button19a = wx.Button(self.panel, -1, "Browse", pos=(13*x_p,23*x_p),
                        size=(round(2.5*x_p), x_p-y_p))
        self.button19a.Bind(wx.EVT_BUTTON, self.on_open_5)
        self.log = wx.TextCtrl(self.panel, -1, pos=(16*x_p, x_p), size=(25*x_p, 22*x_p),
                                       style = wx.TE_MULTILINE|wx.TE_READONLY)
        ##pre-define
        self.dirname5: str = str()
        self.dirname2: str = str()
        self.filename2: str = str()
        self.filename1: str = str()
        self.dirname1: str = str()
        self.dirname0: str = str()
        self.filename0: str = str()
        self.threadx: str = str()
        self.processx: str = str()
        self.dirname5x: str = str()
        self.filename5: str = str()
        self.repx: str = str()
        self.thread1: str = str()
        self.rep2: str = str()

        font1 = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
        		wx.FONTWEIGHT_NORMAL, False, 'Consolas')
        self.log.SetFont(font1)
        self.lblname9.Enable(False)
        self.combo9.Enable(False)
        self.lblname5.Enable(False)
        self.editname5.Enable(False)
        self.lblname6.Enable(False)
        self.editname6.Enable(False)
        self.lblname7.Enable(False)
        self.editname7.Enable(False)
        self.lblname5a.Enable(False)
        self.editname5a.Enable(False)
        self.lblname7a.Enable(False)
        self.editname7a.Enable(False)
        self.lblname6b.Enable(False)
        self.editname6b.Enable(False)
        self.lblname7b.Enable(False)
        self.editname7b.Enable(False)
        self.lblname9a.Enable(False)
        self.txt9a.Enable(False)
        self.button19a.Enable(False)
        self.txt1.Enable(False)
        self.button11.Enable(False)
        self.txt2.Enable(False)
        self.button12.Enable(False)
        self.txt3.Enable(False)
        self.txt4.Enable(False)
        self.lblname8.Enable(False)
        self.combo8.Enable(False)
        self.button18.Enable(False)
        self.lblname9.Enable(False)
        self.clearbutton.Enable(False)
        self.redir=RedirectText(self.log)
        sys.stdout=self.redir
        sys.stderr=self.redir

        self.panel.SetScrollbars( 150, 90,  10, 11 )
        self.panel.SetScrollRate( 3, 3 )

    def on_about(self, event):
        '''about the application'''
        del event
        dlg = wx.MessageDialog(self, 'Wetland DEM Ponding Model version 2.0\t\n'
                                       '\n'
                                       'Copyright (c) 2010, 2012, 2014, 2020 Kevin Shook,'
                                       ' Centre for Hydrology \n'
                                       '--------------------------------------------------\n'
                                       '\n'
                                       'This program is free software: you can redistribute\n'
                                       'it and/or modify it under the terms of the GNU General\n'
                                       'Public License as published bythe'
                                       'Free Software Foundation,\n'
                                       'either version 3 of the License, or (at your option)\n'
                                       'any later version.\n'
                                       'This program is distributed in the hope that it will be\n'
                                       'useful, but WITHOUT ANY WARRANTY;'
                                       'without even the implied\n'
                                       'warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR\n'
                                       ' PURPOSE.  See the GNU General'
                                       'Public License for more details.\n'
                                       '\n'
                                       'You should have received a copy of'
                                       'the GNU General Public License \n'
                                       'along with this program. If not,'
                                       'see <http://www.gnu.org/licenses/>.\n'
                                       '                                        \n'
                                       'From the algorithm of Shapiro,'
                                       'M., & Westervelt, J. (1992). \n'
                                       'An Algebra for GIS and Image Processing (pp. 1-22).\n'
                                       '\n'
                                       'Developed by Oluwaseun Sharomi,'
                                       'Raymond Spiteri and Tonghe Liu\n'
                                       'Numerical Simulation Laboratory,'
                                       'University of Saskatchewan.\n',
                                       'About', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_1(cls):
        '''method check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Invalid method selected.\n', 'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_m1(cls):
        '''method check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please choose whether to use serial or OpenCL.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def on_quit(self, event):
        '''quit'''
        del event
        self.Close(True)

    def process(self, event):
        '''process'''
        del event
        self.runbutton.Enable(True)
        method1 = self.combo8.GetValue()
        if method1=="Serial CPU":
            self.lblname9.Enable(False)
            self.combo9.Enable(False)
        elif method1=="OpenCL":
            self.lblname9.Enable(True)
            self.combo9.Enable(True)
        else:
            self.on_error_m1()

    def en_dis_control(self, lblname5, editname5, lblname6, editname6, lblname7, editname7,
    		lblname5a, editname5a, lblname7a, editname7a, lblname6b, editname6b, lblname7b,
    		editname7b, lblname9a, txt9a, button19a, txt1, button11, txt2, button12, txt3,
    		txt4, lblname8, combo8, button18, lblname9):
        '''disable or enable the button'''
        self.lblname5.Enable(lblname5==1)
        self.editname5.Enable(editname5==1)
        self.lblname6.Enable(lblname6==1)
        self.editname6.Enable(editname6==1)
        self.lblname7.Enable(lblname7==1)
        self.editname7.Enable(editname7==1)
        self.lblname5a.Enable(lblname5a==1)
        self.editname5a.Enable(editname5a==1)
        self.lblname7a.Enable(lblname7a==1)
        self.editname7a.Enable(editname7a==1)
        self.lblname6b.Enable(lblname6b==1)
        self.editname6b.Enable(editname6b==1)
        self.lblname7b.Enable(lblname7b==1)
        self.editname7b.Enable(editname7b==1)
        self.lblname9a.Enable(lblname9a==1)
        self.txt9a.Enable(txt9a==1)
        self.button19a.Enable(button19a==1)
        self.txt1.Enable(txt1==1)
        self.button11.Enable(button11==1)
        self.txt2.Enable(txt2==1)
        self.button12.Enable(button12==1)
        self.txt3.Enable(txt3==1)
        self.txt4.Enable(txt4==1)
        self.lblname8.Enable(lblname8==1)
        self.combo8.Enable(combo8==1)
        self.button18.Enable(button18==1)
        self.lblname9.Enable(lblname9==1)

    def verify(self, event):
        '''verify'''
        del event
        self.button11.Enable(True)
        self.button12.Enable(True)
        self.button19a.Enable(True)
        method = self.combo.GetValue()
        ## activate or deactivate button when using different modules
        if method=='add':
            self.Bind(wx.EVT_MENU, self.en_dis_control(1, 1, 1, 1, 1, 1,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        elif method=='subtract':
            self.Bind(wx.EVT_MENU, self.en_dis_control(0, 0, 0, 0, 0, 0,
            1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        elif method=='drain':
            self.Bind(wx.EVT_MENU, self.en_dis_control(0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        elif method=='TextFile':
            self.Bind(wx.EVT_MENU, self.en_dis_control(0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        else:
            self.on_error_1()

    @classmethod
    def on_error_dem(cls):
        '''dem check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specify DEM filename/path.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_water(cls):
        '''water file check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Water file not selected\n'
                                       'Please use NULL if water file is not required.\n'
                                       , 'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_output(cls):
        '''check output'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specify Output filename.\n'
                                       '\n', 'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_check_point(cls):
        '''output check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Checkpoint filename not specified.\n'
                                       'Please specify NULL if checkpontingPlease specified'
                                       'runoff fraction is not required.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_m2(cls):
        '''method check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please choose whether to use CPU or GPU.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_elev(cls):
        '''elevation hceck'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specify elevation tolerance.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_drain(cls):
        '''drain tolerance check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specify drain tolerance.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_file(cls):
        '''path check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specify Input filename/path.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_depth_s(cls):
        '''sub water check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specified depth of water to subtract.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_depth_a(cls):
        '''add water check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specified depth of water to add.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_error_runoff(cls):
        '''runoff fraction check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'Please specified runoff fraction\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def main_error(cls):
        '''parameter check'''
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       'One or more of the parameters are missing\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    @classmethod
    def on_simulation_finished(cls):
        '''simulation finish?'''
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       'Simulation is not running\n', 'Information',
                                        wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def on_simulation_cancel(self):
        '''cancel simulation'''
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       'Simulation is still running. Cancel running simulation \n',
                                       'Question', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        res = dlg.ShowModal()
        if res==wx.ID_YES:
            self.process.kill()
            self.endbutton.Enable(False)
            print ("==== Simulation Terminated ====")
        dlg.Destroy()

    def on_simulation_close(self):
        '''close simulation'''
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       'Simulation is still running. Close program \n',
                                       'Question', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        res = dlg.ShowModal()
        if res==wx.ID_YES:
            self.process.kill()
            self.Destroy()
        dlg.Destroy()

    def on_simulation_clear(self):
        '''clear simulation'''
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       'Simulation is still running. Clear screen \n',
                                       'Question', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        res = dlg.ShowModal()
        if res==wx.ID_YES:
            self.log.Clear()
            self.clearbutton.Enable(False)
        dlg.Destroy()

    def on_clear_screen(self, event):
        '''clear screen'''
        del event
        alive = self.process.poll()
        if alive is None:
            self.on_simulation_clear()
        else:
            self.log.Clear()
            self.clearbutton.Enable(False)

    def on_abort_button(self, event):
        '''run and end button'''
        del event
        alive = self.process.poll()
        if alive is None:
            self.on_simulation_cancel()
            self.runbutton.Enable(True)
            self.flagz = 0
        else:
            self.on_simulation_finished()
            self.endbutton.Enable(False)

    def report_remove(self):
        '''report.txt'''
        reportfilepath=os.path.join(self.txt0a.GetValue(),"report.txt")
        if os.path.isfile(reportfilepath):
            try:
                os.remove(reportfilepath)
            except Exception:
                raise "Unable to remove file: report.txt" from AssertionError

    def enqueue_output2(self):
        '''enqueue output'''
        lock.acquire()
        try:
            reportfilepath2=os.path.join(self.txt0a.GetValue(),"report.txt")
            try:
                self.rep2 = open(reportfilepath2, "r")
            except Exception:
                raise "Unable to open report.txt" from AssertionError
            readstuff = ''
            while True:
                readstuff = self.rep2.read()
                if readstuff != '':
                    self.redir.write(readstuff)
                if self.process.poll() is not None:
                    self.flagz = 0
                    self.runbutton.Enable(True)
                    self.log.Enable(True)
                    if os.path.isfile(os.path.join(self.txt0a.GetValue(),"temp.asc")):
                        os.remove(os.path.join(self.txt0a.GetValue(),"temp.asc"))
                    if os.path.isfile(os.path.join(self.txt0a.GetValue(),"input1.in")):
                        os.remove(os.path.join(self.txt0a.GetValue(),"input1.in"))
                    if os.path.isfile(os.path.join(self.txt0a.GetValue(),"input2.in")):
                        os.remove(os.path.join(self.txt0a.GetValue(),"input2.in"))
                    break
                self.flagz = 1
            self.rep2.close()
        finally:
            lock.release()

    def module2(self,cmd):
        '''execute command'''
        self.clearbutton.Enable(True)
        self.endbutton.Enable(True)
        self.runbutton.Enable(False)
        self.report_remove()
        reportfilepath=open(os.path.join(self.txt0a.GetValue(),"report.txt"), "w")
        self.process = subprocess.Popen(cmd, stdout=reportfilepath,
                        stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        self.thread1 = threading.Thread(target=self.enqueue_output2)
        self.thread1.daemon = True
        self.thread1.start()

    def cmap(self):
        '''picture converter'''
        lock.acquire()
        try:
            reportfilepathx=os.path.join(self.txt0a.GetValue(),"cmap.txt")
            try:
                self.repx = open(reportfilepathx, "r")
            except Exception:
                raise "Unable to open cmap.txt" from AssertionError
            readstuff = ''
            while True:
                readstuff = self.repx.read()
                if readstuff != '':
                    self.redir.write(readstuff)
                if self.processx.poll() is not None:
                    break
            self.repx.close()
        finally:
            lock.release()

    def on_open_dem(self,event):
        '''open dem file for picture converter'''
        del event
        self.dirname5x = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname5x,"", "*.asc", wx.FD_OPEN)
        if dlg.ShowModal()==wx.ID_OK:
            self.filename5=dlg.GetFilename()
            self.dirname5x=dlg.GetPath()
            self.txt9xa.Clear()
            self.txt9xa.write(self.dirname5x)
            self.convert.Enable(True)
            dlg.Destroy()

    def bitmap_convert(self,event):
        '''picture converter'''
        del event
        reportfilepath=open(os.path.join(self.txt0a.GetValue(),"cmap.txt"), "w")
        if platx in ('Darwin', 'Linux'):
            cmd = ['./cmap_black.sh', self.txt9xa.GetValue()]
            self.processx = subprocess.Popen(cmd, stdout=reportfilepath,
                                stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        else:
            cmd = ['cmap.bat', self.txt9xa.GetValue()]
            self.processx = subprocess.Popen(cmd, stdout=reportfilepath,
                                stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        self.threadx = threading.Thread(target=self.cmap)
        self.threadx.daemon = True
        self.threadx.start()

    def run_sim(self,event):
        '''run simulation'''
        del event
        time.sleep(1)
        self.log.Clear()
        self.log.Enable(True)
        self.run_simulation_optimized()

    ## Run the binary file. Set the parameter according to different module
    def run_simulation_optimized(self):
        '''execute the command'''
        solver=os.getcwd()+"/WDPMCL"
        solverw=os.getcwd()+r"\WDPMCL.exe"
        method = self.combo.GetValue()
        plat = platform.system()
        checkpointfilenamex = os.path.join(self.txt0a.GetValue(),"temp.asc")
        if os.path.isfile(checkpointfilenamex):
            os.remove(checkpointfilenamex)
        if method=='add':
            self.run_simulation_optimized_add()
        elif method=='subtract':
            self.run_simulation_optimized_subtract()
        elif method=='drain':
            self.run_simulation_optimized_drain()
        elif method=='TextFile':
            filename = str(self.txt9a.GetValue())
            if filename=='':
                self.on_error_file()
            else:
                if plat in ('Darwin', 'Linux'):
                    cmd = [solver, filename]
                    self.module2(cmd)
                else:
                    cmd = [solverw, filename]
                    self.module2(cmd)

    def check_file(self):
        '''check the parameter'''
        method1 = self.combo8.GetValue()
        method2 = self.combo9.GetValue()
        demfilename = str(self.txt1.GetValue())
        waterfilename = str(self.txt2.GetValue())
        wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
        checkpointfilename = os.path.join(self.txt0a.GetValue(),"temp.asc")
        elevationtol = str(self.editname7.GetValue())
        if self.txt4.GetValue()=='NULL':
            checkpointfilename = str(self.txt4.GetValue())
        else:
            checkpointfilename = os.path.join(self.txt0a.GetValue(),str(self.txt4.GetValue()))
        if demfilename=='':
            self.on_error_dem()
        if waterfilename=='':
            self.on_error_water()
        if wateroutputfilename=='':
            self.on_error_output()
        if checkpointfilename=='':
            self.on_error_check_point()
        if method1=='':
            self.on_error_m1()
        if method1=='1':
            if method2=='':
                self.on_error_m2()
        if elevationtol=='':
            self.on_error_elev()

    def run_simulation_optimized_add(self):
        '''add module'''
        solver=os.getcwd()+"/WDPMCL"
        solverw=os.getcwd()+r"\WDPMCL.exe"
        method = self.combo.GetValue()
        plat = platform.system()
        method1 = self.combo8.GetValue()
        method2 = self.combo9.GetValue()
        demfilename = str(self.txt1.GetValue())
        waterfilename = str(self.txt2.GetValue())
        wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
        checkpointfilename = os.path.join(self.txt0a.GetValue(),"temp.asc")
        elevationtol = str(self.editname7.GetValue())
        waterdeptha = str(self.editname5.GetValue())
        runoffrac = str(self.editname6.GetValue())
        threshold = str(self.editname10.GetValue())
        limitation = str(self.editname11.GetValue())
        if method1=="Serial CPU":
            method1="0"
        elif method1=="OpenCL":
            method1="1"
        if method2=="GPU":
            method2="1"
        elif method2=="CPU":
            method2="0"
        self.check_file()
        if waterdeptha=='':
            self.on_error_depth_a()
            plat='error'
        if runoffrac=='':
            self.on_error_runoff()
            plat='error'
        if os.path.isfile("self.txt1.GetValue()"):
            pass
        if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue()))):
            pass
        else:
            print ("DEM file not present. Use the Browse button to locate file.")
            plat="error"

        if plat in ('Darwin', 'Linux'):
            cmd = [solver, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdeptha,
                                         runoffrac, elevationtol, method1,
                                          method2, threshold, limitation]
            self.module2(cmd)
        else:
            cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdeptha,
                                         runoffrac, elevationtol, method1,
                                          method2, threshold, limitation]
            self.module2(cmd)

    def run_simulation_optimized_subtract(self):
        '''subtract module'''
        solver=os.getcwd()+"/WDPMCL"
        solverw=os.getcwd()+r"\WDPMCL.exe"
        method = self.combo.GetValue()
        plat = platform.system()
        demfilename = str(self.txt1.GetValue())
        waterfilename = str(self.txt2.GetValue())
        wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
        checkpointfilename = os.path.join(self.txt0a.GetValue(),"temp.asc")
        method1 = self.combo8.GetValue()
        method2 = self.combo9.GetValue()
        waterdepths = str(self.editname5a.GetValue())
        elevationtol = str(self.editname7a.GetValue())
        threshold = str(self.editname10.GetValue())
        limitation = str(self.editname11.GetValue())
        if method1=="Serial CPU":
            method1="0"
        elif method1=="OpenCL":
            method1="1"
        if method2=="GPU":
            method2="1"
        elif method2=="CPU":
            method2="0"
        self.check_file()
        if os.path.isfile("self.txt1.GetValue()"):
            pass
        if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue()))):
            pass
        else:
            print ("DEM file not present. Use the Browse button to locate file.")
            plat="error"
        if waterdepths=='':
            self.on_error_depth_s()
            plat='error'
        if plat in ('Darwin', 'Linux'):
            cmd = [solver, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdepths,
                                         elevationtol, method1, method2,threshold, limitation]
            self.module2(cmd)
        else:
            cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdepths,
                                         elevationtol, method1, method2,threshold, limitation]
            self.module2(cmd)

    def run_simulation_optimized_drain(self):
        '''drain module'''
        solver=os.getcwd()+"/WDPMCL"
        solverw=os.getcwd()+r"\WDPMCL.exe"
        method = self.combo.GetValue()
        plat = platform.system()
        demfilename = str(self.txt1.GetValue())
        waterfilename = str(self.txt2.GetValue())
        wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
        checkpointfilename = os.path.join(self.txt0a.GetValue(),"temp.asc")
        method1 = self.combo8.GetValue()
        method2 = self.combo9.GetValue()
        draintol = str(self.editname6b.GetValue())
        elevationtol = str(self.editname7b.GetValue())
        threshold = str(self.editname10.GetValue())
        limitation = str(self.editname11.GetValue())
        if method1=="Serial CPU":
            method1="0"
        elif method1=="OpenCL":
            method1="1"
        if os.path.isfile("self.txt1.GetValue()"):
            pass
        if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue()))):
            pass
        else:
            print ("DEM file not present. Use the Browse button to locate file.")
            plat="error"
        self.check_file()
        if method2=="GPU":
            method2="1"
        elif method2=="CPU":
            method2="0"
        if draintol=='':
            self.on_error_drain()
            plat='error'
        if plat in ('Darwin', 'Linux'):
            cmd = [solver, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, elevationtol, draintol, method1,
                                         method2,threshold, limitation]
            self.module2(cmd)
        else:
            cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, elevationtol, draintol, method1,
                                        method2,threshold, limitation]
            self.module2(cmd)

    def end_simulation(self, event):
        '''end simulation'''
        del event
        if self.flagz == 1:
            self.on_simulation_close()
        else:
            self.Destroy()

    def on_open_0(self,event):
        '''choose work directory'''
        del event
        self.dirname0 = ''
        dlg = wx.DirDialog(self, "Choose a working directory", style=1)
        if dlg.ShowModal()==wx.ID_OK:
            self.dirname0=dlg.GetPath()
            self.txt0a.Clear()
            self.txt0a.write(self.dirname0)
            self.combo.Enable(True)
            self.txt9xa.Enable(True)
            self.button19xa.Enable(True)
            self.convert.Enable(True)
        dlg.Destroy()

    def on_open_1(self,event):
        '''choose DEM file'''
        del event
        self.dirname1 = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname1,"", "*.asc", wx.FD_OPEN)
        if dlg.ShowModal()==wx.ID_OK:
            self.filename1=dlg.GetFilename()
            self.dirname1=dlg.GetPath()
            self.txt1.Clear()
            self.txt1.write(self.dirname1)
        dlg.Destroy()

    def on_open_2(self,event):
        '''choose water file'''
        del event
        self.dirname2 = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname2,"", "*.asc", wx.FD_OPEN)
        if dlg.ShowModal()==wx.ID_OK:
            self.filename2=dlg.GetFilename()
            self.dirname2=dlg.GetPath()
            self.txt2.Clear()
            self.txt2.write(self.dirname2)
        dlg.Destroy()

    def on_open_5(self,event):
        '''choose text file'''
        del event
        self.dirname5 = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname5,"", "*.txt", wx.FD_OPEN)
        if dlg.ShowModal()==wx.ID_OK:
            self.filename5=dlg.GetFilename()
            self.dirname5=dlg.GetPath()
            self.txt9a.Clear()
            self.txt9a.write(self.dirname5)
            self.runbutton.Enable(True)
        dlg.Destroy()

if __name__=='__main__':
    app=wx.App(redirect=False)
    frame=Size(parent=None,id_=-1)
    frame.Show()
    app.MainLoop()
