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
import queue
import string
import subprocess
import sys
import textwrap
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


if platx=='Darwin' or platx=='Linux':
    if os.path.isfile('cmap_black.sh'):
        pass
    else:
        raise AssertionError("cmap_black.sh not present. Exiting now")

    if os.path.isfile('WDPMCL'):
        pass
    else:
        raise AssertionError("WDPMCL not present. Exiting now")

class RedirectText:
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self,string):
        wx.CallAfter(self.out.WriteText, string)

class CharValidator(wx.PyValidator):
    def __init__(self,flag):
        wx.Validator.__init__(self)
        self.flag=flag
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return CharValidator(self.flag)

    def Validate(self,win):
        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    def OnChar(self, evt):
        key=chr(evt.GetKeyCode())
        if self.flag == "no-alpha" and key in string.ascii_letters:
            return
        if self.flag == "no-digit" and key in string.digits:
            return
        evt.Skip()

class Size(wx.Frame):
    def __init__(self, parent, id_):
        wx.Frame.__init__(self, parent, id_, 'Wetland DEM Ponding Model', size=(1300, 850),
                                  style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|
                                  wx.SYSTEM_MENU|wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN)
        self.panel = wx.ScrolledWindow(self, id_)
        x=35
        y=5

        ## Generate picture (text and button)
        self.lblname9xa = wx.StaticText(self.panel, label="Output to .PNG", pos=(10,25*x))
        self.txt9xa = wx.TextCtrl(self.panel, -1, pos=(round(8*x), round(25*x)),
                        size=(round(2.5*x), round(x-y)))
        self.button19xa = wx.Button(self.panel, -1, "Browse", pos=(round(10.5*x),round(25*x)),
                        size=(round(2.5*x), round(x-y)))
        self.button19xa.Bind(wx.EVT_BUTTON, self.OnOpenDEM)
        self.Convert=wx.Button(self.panel, label="Convert", pos=(round(13*x),round(25*x)),
                        size=(round(2.5*x), round(x-y)))
        self.Convert.Bind(wx.EVT_BUTTON, self.BitmapConvert)
        self.txt9xa.Enable(False)
        self.button19xa.Enable(False)
        self.Convert.Enable(False)

        ## Run the module (text and button)
        self.runbutton=wx.Button(self.panel, label="Start", pos=(round(10),round(24*x)),
                        size=(round(2.5*x), round(x-y)))
        self.clearbutton=wx.Button(self.panel, label="Clear",
        		pos=(8*x,24*x), size=(round(2.5*x), x-y))
        self.endbutton=wx.Button(self.panel, label="End", pos=(13*x,24*x), size=(round(2.5*x), x-y))
        self.Bind(wx.EVT_BUTTON, self.RunSim, self.runbutton)
        self.Bind(wx.EVT_BUTTON, self.OnClearScreen, self.clearbutton)
        self.Bind(wx.EVT_BUTTON, self.OnAbortButton, self.endbutton)
        self.runbutton.Enable(False)
        self.endbutton.Enable(False)
        self.Bind(wx.EVT_CLOSE,self.EndSimulation)

        ## Menu (text and button)
        self.flagz = 0
        menubar = wx.MenuBar()
        filez = wx.Menu()
        quit = wx.MenuItem(filez, 1, '&Quit\tCtrl+Q')
        about = wx.MenuItem(filez, 3, '&About\tCtrl+A')
        filez.Append(quit)
        filez.Append(about)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=1)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=3)
        menubar.Append(filez, '&File')
        self.SetMenuBar(menubar)
        self.Show(True)

        ## Working directory (text and button)
        self.lblname0a = wx.StaticText(self.panel, label="Working Directory:", pos=(10,x))
        self.txt0a = wx.TextCtrl(self.panel, -1, pos=(8*x, x), size=(5*x, x-y))
        self.button00a = wx.Button(self.panel, -1, "Browse", pos=(13*x,x), size=(round(2.5*x), x-y))
        self.button00a.Bind(wx.EVT_BUTTON, self.OnOpen0)

        ## Choose module (text and button)
        methods = [" ", "add", "subtract", "drain", "TextFile"]
        self.lblname0 = wx.StaticText(self.panel, label="Methods:", pos=(10,2*x))
        self.combo = wx.ComboBox(self.panel, -1, pos=(8*x, 2*x), size=(5*x, x-y),
                        choices=methods, style=wx.CB_READONLY)
        self.combo.Bind(wx.EVT_COMBOBOX, self.Verify)
        self.combo.Enable(False)

        ## Set DEM, water, output and scratch files (text and button)
        self.lblname1 = wx.StaticText(self.panel, label="DEM File:", pos=(10,3*x))
        self.txt1 = wx.TextCtrl(self.panel, -1, pos=(8*x, 3*x), size=(5*x, x-y))
        self.button11 = wx.Button(self.panel, -1, "Browse",
        		pos=(13*x,3*x), size=(round(2.5*x), x-y))
        self.button11.Bind(wx.EVT_BUTTON, self.OnOpen1)
        self.lblname2 = wx.StaticText(self.panel, label="Water File:", pos=(10,4*x))
        self.txt2 = wx.TextCtrl(self.panel, -1, pos=(8*x, 4*x),
        		size=(5*x, x-y),value='NULL')
        self.button12 = wx.Button(self.panel, -1, "Browse",
        		pos=(13*x,4*x), size=(round(2.5*x), x-y))
        self.button12.Bind(wx.EVT_BUTTON, self.OnOpen2)
        self.lblname3 = wx.StaticText(self.panel, label="Output File:", pos=(10,5*x))
        self.txt3 = wx.TextCtrl(self.panel, -1, pos=(8*x, 5*x), size=(5*x, x-y),value='water.asc')
        self.lblname4 = wx.StaticText(self.panel, label="Scratch File:", pos=(10,6*x))
        self.txt4 = wx.TextCtrl(self.panel, -1, pos=(8*x, 6*x), size=(5*x, x-y),value='NULL')

        ## Add Components
        self.lblname50 = wx.StaticText(self.panel, label="Add Components", pos=(10,7*x))
        self.lblname5 = wx.StaticText(self.panel, label="Depth of water (mm):", pos=(10,8*x))
        self.editname5 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,8*x),value='10',
                        validator=CharValidator("no-alpha"))
        self.lblname6 = wx.StaticText(self.panel, label="Water runoff fraction:", pos=(10,9*x))
        self.editname6 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,9*x),value='1',
                        validator=CharValidator("no-alpha"))
        self.lblname7 = wx.StaticText(self.panel, label="Elevation tolerance (mm):", pos=(10,10*x))
        self.editname7 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,10*x),value='1',
                        validator=CharValidator("no-alpha"))

        ## Subtract Components
        self.lblname5a0 = wx.StaticText(self.panel, label="Subtract Components", pos=(10,11*x))
        self.lblname5a = wx.StaticText(self.panel, label="Depth of water (mm):", pos=(10,12*x))
        self.editname5a = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,12*x),value='1',
                        validator=CharValidator("no-alpha"))
        self.lblname7a = wx.StaticText(self.panel, label="Elevation tolerance (mm):", pos=(10,13*x))
        self.editname7a = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,13*x),value='1',
                        validator=CharValidator("no-alpha"))

        ## Drain Components
        self.lblname6b0 = wx.StaticText(self.panel, label="Drain Components", pos=(10,14*x))
        self.lblname6b = wx.StaticText(self.panel, label="Elevation tolerance (mm):", pos=(10,15*x))
        self.editname6b = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,15*x),value='1',
                        validator=CharValidator("no-alpha"))
        self.lblname7b = wx.StaticText(self.panel, label="Drain tolerance (m3):", pos=(10,16*x))
        self.editname7b = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,16*x),value='1',
                        validator=CharValidator("no-alpha"))

        ## Other Components
        self.lblname6bz = wx.StaticText(self.panel, label="Computation Settings", pos=(10,17*x))
        methods1 = [" ", "Serial CPU", "OpenCL"]
        self.lblname8 = wx.StaticText(self.panel, label="Serial/OpenCL:", pos=(10,18*x))
        self.combo8 = wx.ComboBox(self.panel, -1, pos=(8*x, 18*x), size=(5*x, x-y),
                        choices=methods1, style=wx.CB_READONLY)
        self.button18 = wx.Button(self.panel, -1, "Process", pos=(13*x,18*x),
        		 size=(round(2.5*x), x-y))
        self.button18.Bind(wx.EVT_BUTTON, self.Process)
        methods2 = [" ", "GPU", "CPU"]
        self.lblname9 = wx.StaticText(self.panel, label="OpenCL CPU/GPU:", pos=(10,19*x))
        self.combo9 = wx.ComboBox(self.panel, -1, pos=(8*x, 19*x), size=(5*x, x-y),
                                          choices=methods2, style=wx.CB_READONLY)

        ## water depth threshold component
        self.lblname10 = wx.StaticText(self.panel, label="Zero depth threshold value (mm):",
                        pos=(10,20*x))
        self.editname10 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,20*x),value='0',
                        validator=CharValidator("no-alpha"))
        self.lblname11 = wx.StaticText(self.panel,
                         label="Iteration limitation (0 if no limitation):", pos=(10,21*x))
        self.editname11 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,21*x),value='0',
                        validator=CharValidator("no-alpha"))

        ## Load variables from a file
        self.lblname9a0 = wx.StaticText(self.panel, label="Load from file", pos=(10,22*x))
        self.lblname9a = wx.StaticText(self.panel, label="Text File:", pos=(10,23*x))
        self.txt9a = wx.TextCtrl(self.panel, -1, pos=(8*x, 23*x), size=(5*x, x-y))
        self.button19a = wx.Button(self.panel, -1, "Browse", pos=(13*x,23*x),
                        size=(round(2.5*x), x-y))
        self.button19a.Bind(wx.EVT_BUTTON, self.OnOpen5)
        self.log = wx.TextCtrl(self.panel, -1, pos=(16*x, x), size=(25*x, 22*x),
                                       style = wx.TE_MULTILINE|wx.TE_READONLY)

        font1 = wx.Font(11, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Consolas')
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

    def OnAbout(self, event):
        dlg = wx.MessageDialog(self, 'Wetland DEM Ponding Model version 2.0\t\n'
                                       '\n'
                                       'Copyright (c) 2010, 2012, 2014, 2020 Kevin Shook, Centre for Hydrology \n'
                                       '--------------------------------------------------------------------\n'
                                       '\n'
                                       'This program is free software: you can redistribute\n'
                                       'it and/or modify it under the terms of the GNU General\n'
                                       'Public License as published bythe Free Software Foundation,\n'
                                       'either version 3 of the License, or (at your option)\n'
                                       'any later version.\n'
                                       'This program is distributed in the hope that it will be\n'
                                       'useful, but WITHOUT ANY WARRANTY; without even the implied\n'
                                       'warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR\n'
                                       ' PURPOSE.  See the GNU General Public License for more details.\n'
                                       '\n'
                                       'You should have received a copy of the GNU General Public License \n'
                                       'along with this program. If not, see <http://www.gnu.org/licenses/>.\n'
                                       '                                                                \n'
                                       'From the algorithm of Shapiro, M., & Westervelt, J. (1992). \n'
                                       'An Algebra for GIS and Image Processing (pp. 1-22).\n'
                                       '\n'
                                       'Developed by Oluwaseun Sharomi, Raymond Spiteri and Tonghe Liu\n'
                                       'Numerical Simulation Laboratory, University of Saskatchewan.\n',
                                       'About', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def OnError1(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Invalid method selected.\n', 'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorM1(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please choose whether to use serial or OpenCL.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnQuit(self, event):
        self.Close(True)

    def Process(self, event):
        self.runbutton.Enable(True)
        method1 = self.combo8.GetValue()
        if method1=="Serial CPU":
            self.lblname9.Enable(False)
            self.combo9.Enable(False)
        elif method1=="OpenCL":
            self.lblname9.Enable(True)
            self.combo9.Enable(True)
        else:
            self.OnErrorM1()

    def En_Dis_Control(self, lblname5, editname5, lblname6, editname6, lblname7, editname7,
    		lblname5a, editname5a, lblname7a, editname7a, lblname6b, editname6b, lblname7b,
    		editname7b, lblname9a, txt9a, button19a, txt1, button11, txt2, button12, txt3,
    		txt4, lblname8, combo8, button18, lblname9):
        self.lblname5.Enable(True) if lblname5==1 else self.lblname5.Enable(False)
        self.editname5.Enable(True) if editname5==1 else self.editname5.Enable(False)
        self.lblname6.Enable(True) if lblname6==1 else self.lblname6.Enable(False)
        self.editname6.Enable(True) if editname6==1 else self.editname6.Enable(False)
        self.lblname7.Enable(True) if lblname7==1 else self.lblname7.Enable(False)
        self.editname7.Enable(True) if editname7==1 else self.editname7.Enable(False)
        self.lblname5a.Enable(True) if lblname5a==1 else self.lblname5a.Enable(False)
        self.editname5a.Enable(True) if editname5a==1 else self.editname5a.Enable(False)
        self.lblname7a.Enable(True) if lblname7a==1 else self.lblname7a.Enable(False)
        self.editname7a.Enable(True) if editname7a==1 else self.editname7a.Enable(False)
        self.lblname6b.Enable(True) if lblname6b==1 else self.lblname6b.Enable(False)
        self.editname6b.Enable(True) if editname6b==1 else self.editname6b.Enable(False)
        self.lblname7b.Enable(True) if lblname7b==1 else self.lblname7b.Enable(False)
        self.editname7b.Enable(True) if editname7b==1 else self.editname7b.Enable(False)
        self.lblname9a.Enable(True) if lblname9a==1 else self.lblname9a.Enable(False)
        self.txt9a.Enable(True) if txt9a==1 else self.txt9a.Enable(False)
        self.button19a.Enable(True) if button19a==1 else self.button19a.Enable(False)
        self.txt1.Enable(True) if txt1==1 else self.txt1.Enable(False)
        self.button11.Enable(True) if button11==1 else self.button11.Enable(False)
        self.txt2.Enable(True) if txt2==1 else self.txt2.Enable(False)
        self.button12.Enable(True) if button12==1 else self.button12.Enable(False)
        self.txt3.Enable(True) if txt3==1 else self.txt3.Enable(False)
        self.txt4.Enable(True) if txt4==1 else self.txt4.Enable(False)
        self.lblname8.Enable(True) if lblname8==1 else self.lblname8.Enable(False)
        self.combo8.Enable(True) if combo8==1 else self.combo8.Enable(False)
        self.button18.Enable(True) if button18==1 else self.button18.Enable(False)
        self.lblname9.Enable(True) if lblname9==1 else self.lblname9.Enable(False)

    def Verify(self, event):
        self.button11.Enable(True)
        self.button12.Enable(True)
        self.button19a.Enable(True)
        method = self.combo.GetValue()

        ## activate or deactivate button when using different modules
        if method=='add':
            self.Bind(wx.EVT_MENU, self.En_Dis_Control(1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        elif method=='subtract':
            self.Bind(wx.EVT_MENU, self.En_Dis_Control(0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        elif method=='drain':
            self.Bind(wx.EVT_MENU, self.En_Dis_Control(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        elif method=='TextFile':
            self.Bind(wx.EVT_MENU, self.En_Dis_Control(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        else:
            self.OnError1()


    def OnErrorDem(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specify DEM filename/path.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorWater(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Water file not selected\n'
                                       '\n'
                                       'Please use NULL if water file is not required.\n'
                                       , 'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorOutput(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specify Output filename.\n'
                                       '\n', 'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorCheckpoint(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Checkpoint filename not specified.\n'
                                       '\n'
                                       'Please specify NULL if checkpontingPlease specified runoff fraction is not required.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorM2(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please choose whether to use CPU or GPU.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorElev(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specify elevation tolerance.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorDrain(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specify drain tolerance.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorFile(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specify Input filename/path.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorDepthS(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specified depth of water to subtract.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorDepthA(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specified depth of water to add.\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnErrorRunOff(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'Please specified runoff fraction\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def MainError(self):
        dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
                                       '\n'
                                       'One or more of the parameters are missing\n',
                                        'Error', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def OnSimulationFinished(self):
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       '\n'
                                       'Simulation is not running\n', 'Information',
                                        wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def OnSimulationCancel(self):
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       '\n'
                                       'Simulation is still running. Cancel running simulation \n',
                                       'Question', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        res = dlg.ShowModal()
        if res==wx.ID_YES:
            self.process.kill()
            self.endbutton.Enable(False)
            print ("==== Simulation Terminated ====")
        dlg.Destroy()

    def OnSimulationClose(self):
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       '\n'
                                       'Simulation is still running. Close program \n',
                                       'Question', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        res = dlg.ShowModal()
        if res==wx.ID_YES:
            self.process.kill()
            self.Destroy()
        dlg.Destroy()

    def OnSimulationClear(self):
        dlg = wx.MessageDialog(None, 'WDPM\t\n'
                                       '\n'
                                       'Simulation is still running. Clear screen \n',
                                       'Question', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        res = dlg.ShowModal()
        if res==wx.ID_YES:
            self.log.Clear()
            self.clearbutton.Enable(False)
        dlg.Destroy()

    def OnClearScreen(self, event):
        alive = self.process.poll()
        if alive is None:
            self.OnSimulationClear()
        else:
            self.log.Clear()
            self.clearbutton.Enable(False)

    def OnAbortButton(self, event):
        alive = self.process.poll()
        if alive is None:
            self.OnSimulationCancel()
            self.runbutton.Enable(True)
            self.flagz = 0
        else:
            self.OnSimulationFinished()
            self.endbutton.Enable(False)

    def Reportremove(self):
        reportfilepath=os.path.join(self.txt0a.GetValue(),"report.txt")
        if os.path.isfile(reportfilepath):
            try:
                os.remove(reportfilepath)
            except Exception:
                print ("Unable to remove file: report.txt")

    def enqueue_output(self, cmd):
        lock.acquire()
        try:
            reportfilepath1=os.path.join(self.txt0a.GetValue(),"report.txt")
            try:
                self.rep1 = open(reportfilepath1, "r")
            except Exception:
                raise AssertionError("Unable to open report.txt")
            readstuff = ''
            while True:
                readstuff = self.rep1.read()
                if readstuff != '':
                    #self.redir.write(readstuff)
                    print ("Please wait ........................")
                if self.process0.poll() is not None:
                    self.flagz = 0
                    break
                else:
                    self.flagz = 1
            self.rep1.close()
            self.Module2(cmd)
        finally:
            lock.release()

    def enqueue_output2(self):
        lock.acquire()
        try:
            reportfilepath2=os.path.join(self.txt0a.GetValue(),"report.txt")
            try:
                self.rep2 = open(reportfilepath2, "r")
            except Exception:
                raise AssertionError("Unable to open report.txt")
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
                else:
                    self.flagz = 1
            self.rep2.close()
        finally:
            lock.release()

    def Module2(self,cmd):
        self.clearbutton.Enable(True)
        self.endbutton.Enable(True)
        self.runbutton.Enable(False)
        self.Reportremove()
        reportfilepath=open(os.path.join(self.txt0a.GetValue(),"report.txt"), "w")
        self.process = subprocess.Popen(cmd, stdout=reportfilepath,
                        stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        self.thread1 = threading.Thread(target=self.enqueue_output2)
        self.thread1.daemon = True
        self.thread1.start()

    def cmap(self):
        lock.acquire()
        try:
            reportfilepathx=os.path.join(self.txt0a.GetValue(),"cmap.txt")
            try:
                self.repx = open(reportfilepathx, "r")
            except Exception:
                raise AssertionError("Unable to open cmap.txt")
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

        ## Open DEM file for the picture converting
    def OnOpenDEM(self,event):
        self.dirname5x = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname5x,"", "*.asc", wx.FD_OPEN)
        if dlg.ShowModal()==wx.ID_OK:
            self.filename5=dlg.GetFilename()
            self.dirname5x=dlg.GetPath()
            self.txt9xa.Clear()
            self.txt9xa.write(self.dirname5x)
            self.Convert.Enable(True)
            dlg.Destroy()

    def BitmapConvert(self,event):
        reportfilepath=open(os.path.join(self.txt0a.GetValue(),"cmap.txt"), "w")
        platx = platform.system()
        if platx=='Darwin' or platx=='Linux':
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

    def RunSim(self,event):
        time.sleep(1)
        self.log.Clear()
        self.log.Enable(True)
        self.RunSimulationOptimized()

    ## Run the binary file. Set the parameter according to different module
    def RunSimulationOptimized(self):
        solver=os.getcwd()+"/WDPMCL"
        solverw=os.getcwd()+"\WDPMCL.exe"
        method = self.combo.GetValue()
        plat = platform.system()
        checkpointfilenamex = os.path.join(self.txt0a.GetValue(),"temp.asc")
        if os.path.isfile(checkpointfilenamex):
            os.remove(checkpointfilenamex)
        if method=='add':
            demfilename = str(self.txt1.GetValue())
            waterfilename = str(self.txt2.GetValue())
            wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
            if self.txt4.GetValue()=='NULL':
                checkpointfilename = str(self.txt4.GetValue())
            else:
                checkpointfilename = os.path.join(self.txt0a.GetValue(),str(self.txt4.GetValue()))
            method1 = self.combo8.GetValue()
            method2 = self.combo9.GetValue()
            waterdeptha = str(self.editname5.GetValue())
            runoffrac = str(self.editname6.GetValue())
            elevationtol = str(self.editname7.GetValue())
            threshold = str(self.editname10.GetValue())
            limitation = str(self.editname11.GetValue())
            if method1=="Serial CPU":
                method1="0"
            elif method1=="OpenCL":
                method1="1"

            if method2=="GPU":
                method2="0"
            elif method2=="CPU":
                method2="1"

            if demfilename=='':
                self.OnErrorDem()
                plat='error'
            if waterfilename=='':
                self.OnErrorWater()
                plat='error'
            if wateroutputfilename=='':
                self.OnErrorOutput()
                plat='error'
            if checkpointfilename=='':
                self.OnErrorCheckpoint()
                plat='error'
            if method1=='':
                self.OnErrorM1()
                plat='error'
            if method1=='1':
                if method2=='':
                    self.OnErrorM2()
                    plat='error'
            if elevationtol=='':
                self.OnErrorElev()
                plat='error'
            if waterdeptha=='':
                self.OnErrorDepthA()
                plat='error'
            if runoffrac=='':
                self.OnErrorRunOff()
                plat='error'

            if os.path.isfile("self.txt1.GetValue()"):
                pass
            if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue()))):
                pass
            else:
                print ("DEM file not present. Use the Browse button to locate file.")
                plat="error"

            if plat=='Darwin' or plat=='Linux':
                cmd = [solver, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdeptha,
                                         runoffrac, elevationtol, method1, method2, threshold, limitation]
                self.Module2(cmd)
            else:
                cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdeptha,
                                         runoffrac, elevationtol, method1, method2, threshold, limitation]
                self.Module2(cmd)
        elif method=='subtract':
            demfilename = str(self.txt1.GetValue())
            waterfilename = str(self.txt2.GetValue())
            wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
            if self.txt4.GetValue()=='NULL':
                checkpointfilename = str(self.txt4.GetValue())
            else:
                checkpointfilename = os.path.join(self.txt0a.GetValue(),str(self.txt4.GetValue()))
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
                method2="0"
            elif method2=="CPU":
                method2="1"

            if os.path.isfile("self.txt1.GetValue()"):
                pass
            if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue()))):
                pass
            else:
                print ("DEM file not present. Use the Browse button to locate file.")
                plat="error"

            if demfilename=='':
                self.OnErrorDem()
                plat='error'
            if waterfilename=='':
                self.OnErrorWater()
                plat='error'
            if wateroutputfilename=='':
                self.OnErrorOutput()
                plat='error'
            if checkpointfilename=='':
                self.OnErrorCheckpoint()
                plat='error'
            if method1=='':
                self.OnErrorM1()
                plat='error'
            if method1=='1':
                if method2=='':
                    self.OnErrorM2()
                    plat='error'
            if elevationtol=='':
                self.OnErrorElev()
                plat='error'
            if waterdepths=='':
                self.OnErrorDepthS()
                plat='error'
            if plat=='Darwin' or plat=='Linux':
                cmd = [solver, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdepths,
                                         elevationtol, method1, method2,threshold, limitation]
                self.Module2(cmd)
            else:
                cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, waterdepths,
                                         elevationtol, method1, method2,threshold, limitation]
                self.Module2(cmd)
        elif method=='drain':
            demfilename = str(self.txt1.GetValue())
            waterfilename = str(self.txt2.GetValue())
            wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
            if self.txt4.GetValue()=='NULL':
                checkpointfilename = str(self.txt4.GetValue())
            else:
                checkpointfilename = os.path.join(self.txt0a.GetValue(),str(self.txt4.GetValue()))
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

            if method2=="GPU":
                method2="0"
            elif method2=="CPU":
                method2="1"

            if demfilename=='':
                self.OnErrorDem()
                plat='error'
            if waterfilename=='':
                self.OnErrorWater()
                plat='error'
            if wateroutputfilename=='':
                self.OnErrorOutput()
                plat='error'
            if checkpointfilename=='':
                self.OnErrorCheckpoint()
            if method1=='':
                self.OnErrorM1()
                plat='error'
            if method1=='1':
                if method2=='':
                    self.OnErrorM2()
                    plat='error'
            if elevationtol=='':
                self.OnErrorElev()
                plat='error'
            if draintol=='':
                self.OnErrorDrain()
                plat='error'
            if plat=='Darwin' or plat=='Linux':
                cmd = [solver, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, elevationtol, draintol, method1,
                                         method2,threshold, limitation]
                self.Module2(cmd)
            else:
                cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename,
                                        checkpointfilename, elevationtol, draintol, method1,
                                        method2,threshold, limitation]
                self.Module2(cmd)
        elif method=='TextFile':
            filename = str(self.txt9a.GetValue())
            if filename=='':
                self.OnErrorFile()
            else:
                if plat=='Darwin' or plat=='Linux':
                    cmd = [solver, filename]
                    self.Module2(cmd)
                else:
                    cmd = [solverw, filename]
                    self.Module2(cmd)

    def EndSimulation(self, event):
        if self.flagz == 1:
            self.OnSimulationClose()
        else:
            self.Destroy()

    ## Open working directory
    def OnOpen0(self,event):
        self.dirname0 = ''
        dlg = wx.DirDialog(self, "Choose a working directory", style=1)
        if dlg.ShowModal()==wx.ID_OK:
            self.dirname0=dlg.GetPath()
            self.txt0a.Clear()
            self.txt0a.write(self.dirname0)
            self.combo.Enable(True)
            self.txt9xa.Enable(True)
            self.button19xa.Enable(True)
            self.Convert.Enable(True)
        dlg.Destroy()

    ## Open DEM file
    def OnOpen1(self,event):
        self.dirname1 = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname1,"", "*.asc", wx.FD_OPEN)
        if dlg.ShowModal()==wx.ID_OK:
            self.filename1=dlg.GetFilename()
            self.dirname1=dlg.GetPath()
            self.txt1.Clear()
            self.txt1.write(self.dirname1)
        dlg.Destroy()

    ## Open water file
    def OnOpen2(self,event):
        self.dirname2 = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname2,"", "*.asc", wx.FD_OPEN)
        if dlg.ShowModal()==wx.ID_OK:
            self.filename2=dlg.GetFilename()
            self.dirname2=dlg.GetPath()
            self.txt2.Clear()
            self.txt2.write(self.dirname2)
        dlg.Destroy()

    ## 'Textfile' function
    def OnOpen5(self,event):
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
