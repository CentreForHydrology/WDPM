import wx
import os
import sys
import string
import platform
import subprocess
import threading
import time
import textwrap
import lzma

lock = threading.Lock()
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x


if os.path.isfile('runoff.cl')==True:
    pass
else:
    raise AssertionError("runoff.cl not present. Exiting now")
if os.path.isfile('colormap_black.txt')==True:
    pass
else:
    raise AssertionError("colormap_black.txt not present. Exiting now")

platx = platform.system()


if platx=='Darwin' or platx=='Linux':
	if os.path.isfile('cmap_black.sh')==True:
	    pass
	else:
	    raise AssertionError("cmap_black.sh not present. Exiting now")

	if os.path.isfile('WDPMCL')==True:
	    pass
	else:
	    raise AssertionError("WDPMCL not present. Exiting now")
else:
	import win32com.client
	if os.path.isfile('cmap.bat')==True:
	    pass
	else:
	    raise AssertionError("cmap.bat not present. Exiting now")
	
	if os.path.isfile('WDPMCL.exe')==True:
	    pass
	else:
	    raise AssertionError("WDPMCL.exe not present. Exiting now")

class RedirectText:
	def __init__(self,aWxTextCtrl):
	    self.out=aWxTextCtrl

	def write(self,string):
	    wx.CallAfter(self.out.WriteText, string)

class CharValidator(wx.PyValidator):
	def __init__(self,flag):
		wx.PyValidator.__init__(self)
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
		wx.Frame.__init__(self, parent, id_, 'WDPM Program', size=(1366, 768),
				  style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.SYSTEM_MENU|
				  wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN)
		self.panel = wx.PyScrolledWindow(self, id_)
		#self.panel=wx.Panel(self)
		x=25
		y=5
		
		self.lblname9xa = wx.StaticText(self.panel, label="Output to .PNG", pos=(10,23*x))
		self.txt9xa = wx.TextCtrl(self.panel, -1, pos=(8*x, 23*x), size=(2.5*x, x-y))
		self.button19xa = wx.Button(self.panel, -1, "Browse", pos=(10.5*x,23*x), size=(2.5*x, x-y))
		self.button19xa.Bind(wx.EVT_BUTTON, self.OnOpenDEM)
		self.Convert=wx.Button(self.panel, label="Convert", pos=(13*x,23*x), size=(2.5*x, x-y))
		self.Convert.Bind(wx.EVT_BUTTON, self.BitmapConvert)
		self.txt9xa.Enable(False)
		self.button19xa.Enable(False)
		self.Convert.Enable(False)
		self.runbutton=wx.Button(self.panel, label="Start", pos=(10,22*x), size=(2.5*x, x-y))
		self.clearbutton=wx.Button(self.panel, label="Clear", pos=(8*x,22*x), size=(2.5*x, x-y))
		self.endbutton=wx.Button(self.panel, label="End", pos=(13*x,22*x), size=(2.5*x, x-y))
		self.Bind(wx.EVT_BUTTON, self.RunSim, self.runbutton)
		self.Bind(wx.EVT_BUTTON, self.OnClearScreen, self.clearbutton)		
		self.Bind(wx.EVT_BUTTON, self.OnAbortButton, self.endbutton)
		self.runbutton.Enable(False)
		self.endbutton.Enable(False)
		self.Bind(wx.EVT_CLOSE,self.EndSimulation)
		self.flagz = 0
		menubar = wx.MenuBar()
		filez = wx.Menu()
		quit = wx.MenuItem(filez, 1, '&Quit\tCtrl+Q')
		about = wx.MenuItem(filez, 3, '&About\tCtrl+A')
		filez.AppendItem(quit)
		filez.AppendItem(about)
		self.Bind(wx.EVT_MENU, self.OnQuit, id=1)
		self.Bind(wx.EVT_MENU, self.OnAbout, id=3)
		menubar.Append(filez, '&File')
		self.SetMenuBar(menubar)
		self.Show(True)

		self.lblname0a = wx.StaticText(self.panel, label="Working Directory:", pos=(10,x))
		self.txt0a = wx.TextCtrl(self.panel, -1, pos=(8*x, x), size=(5*x, x-y))
		self.button00a = wx.Button(self.panel, -1, "Browse", pos=(13*x,x), size=(2.5*x, x-y))
		self.button00a.Bind(wx.EVT_BUTTON, self.OnOpen0)
		methods = [" ", "add", "subtract", "drain", "TextFile"]
		self.lblname0 = wx.StaticText(self.panel, label="Methods:", pos=(10,2*x))
		self.combo = wx.ComboBox(self.panel, -1, pos=(8*x, 2*x), size=(5*x, x-y), choices=methods, style=wx.CB_READONLY)
		wx.EVT_COMBOBOX(self,self.combo.GetId(),self.Verify)
		#self.button10 = wx.Button(self.panel, -1, "Verify", pos=(13*x,2*x), size=(2.5*x, x-y))
		#self.button10.Bind(wx.EVT_BUTTON, self.Verify)
		self.combo.Enable(False)
		self.lblname1 = wx.StaticText(self.panel, label="DEM File:", pos=(10,3*x))
		self.txt1 = wx.TextCtrl(self.panel, -1, pos=(8*x, 3*x), size=(5*x, x-y))
		self.button11 = wx.Button(self.panel, -1, "Browse", pos=(13*x,3*x), size=(2.5*x, x-y))
		self.button11.Bind(wx.EVT_BUTTON, self.OnOpen1)
		self.lblname2 = wx.StaticText(self.panel, label="Water File:", pos=(10,4*x))
		self.txt2 = wx.TextCtrl(self.panel, -1, pos=(8*x, 4*x), size=(5*x, x-y),value='NULL')
		self.button12 = wx.Button(self.panel, -1, "Browse", pos=(13*x,4*x), size=(2.5*x, x-y))
		self.button12.Bind(wx.EVT_BUTTON, self.OnOpen2)
		self.lblname3 = wx.StaticText(self.panel, label="Output File:", pos=(10,5*x))
		self.txt3 = wx.TextCtrl(self.panel, -1, pos=(8*x, 5*x), size=(5*x, x-y),value='water.asc')
		self.lblname4 = wx.StaticText(self.panel, label="Scratch File:", pos=(10,6*x))
		self.txt4 = wx.TextCtrl(self.panel, -1, pos=(8*x, 6*x), size=(5*x, x-y),value='NULL')
		## Add Components
		self.lblname50 = wx.StaticText(self.panel, label="Add Components", pos=(10,7*x))
		self.lblname5 = wx.StaticText(self.panel, label="Depth of water (mm):", pos=(10,8*x))
		self.editname5 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,8*x),value='10',validator=CharValidator("no-alpha"))
		self.lblname6 = wx.StaticText(self.panel, label="Water runoff fraction:", pos=(10,9*x))
		self.editname6 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,9*x),value='1',validator=CharValidator("no-alpha"))	                  
		self.lblname7 = wx.StaticText(self.panel, label="Elevation tolerance (mm):", pos=(10,10*x))
		self.editname7 = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,10*x),value='1',validator=CharValidator("no-alpha"))
		## Subtract Components
		self.lblname5a0 = wx.StaticText(self.panel, label="Subtract Components", pos=(10,11*x))
		self.lblname5a = wx.StaticText(self.panel, label="Depth of water (mm):", pos=(10,12*x))
		self.editname5a = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,12*x),value='1',validator=CharValidator("no-alpha"))	                  
		self.lblname7a = wx.StaticText(self.panel, label="Elevation tolerance (mm):", pos=(10,13*x))
		self.editname7a = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,13*x),value='1',validator=CharValidator("no-alpha"))
		## Drain Components
		self.lblname6b0 = wx.StaticText(self.panel, label="Drain Components", pos=(10,14*x))
		self.lblname6b = wx.StaticText(self.panel, label="Elevation tolerance (mm):", pos=(10,15*x))
		self.editname6b = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,15*x),value='1',validator=CharValidator("no-alpha"))	                  
		self.lblname7b = wx.StaticText(self.panel, label="Drain tolerance (m3):", pos=(10,16*x))
		self.editname7b = wx.TextCtrl(self.panel, size=(5*x, x-y), pos=(8*x,16*x),value='1',validator=CharValidator("no-alpha"))
		## Other Components
		self.lblname6bz = wx.StaticText(self.panel, label="Computation Settings", pos=(10,17*x))
		methods1 = [" ", "Serial CPU", "OpenCL"]
		self.lblname8 = wx.StaticText(self.panel, label="Serial/OpenCL:", pos=(10,18*x))
		self.combo8 = wx.ComboBox(self.panel, -1, pos=(8*x, 18*x), size=(5*x, x-y), choices=methods1, style=wx.CB_READONLY)
		self.button18 = wx.Button(self.panel, -1, "Process", pos=(13*x,18*x), size=(2.5*x, x-y))
		self.button18.Bind(wx.EVT_BUTTON, self.Process)                   
		methods2 = [" ", "GPU", "CPU"]
		self.lblname9 = wx.StaticText(self.panel, label="OpenCL CPU/GPU:", pos=(10,19*x))
		self.combo9 = wx.ComboBox(self.panel, -1, pos=(8*x, 19*x), size=(5*x, x-y), 
			                  choices=methods2, style=wx.CB_READONLY)                
		## Load variables from a file
		self.lblname9a0 = wx.StaticText(self.panel, label="Load from file", pos=(10,20*x))
		self.lblname9a = wx.StaticText(self.panel, label="Text File:", pos=(10,21*x))
		self.txt9a = wx.TextCtrl(self.panel, -1, pos=(8*x, 21*x), size=(5*x, x-y))
		self.button19a = wx.Button(self.panel, -1, "Browse", pos=(13*x,21*x), size=(2.5*x, x-y))
		self.button19a.Bind(wx.EVT_BUTTON, self.OnOpen5)
		self.log = wx.TextCtrl(self.panel, -1, pos=(16*x, x), size=(25*x, 22*x), 
			               style = wx.TE_MULTILINE|wx.TE_READONLY)
		font1 = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier')
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
		#self.button13.Enable(False)
		self.txt4.Enable(False)
		#self.button14.Enable(False)		  
		self.lblname8.Enable(False)
		self.combo8.Enable(False)
		self.button18.Enable(False)
		self.lblname9.Enable(False)
		self.clearbutton.Enable(False)	
		self.redir=RedirectText(self.log)
		sys.stdout=self.redir
		sys.stderr=self.redir

		self.panel.SetScrollbars( 150, 80,  10, 10 )
		self.panel.SetScrollRate( 3, 3 )


	def OnAbout(self, event):
		dlg = wx.MessageDialog(self, 'Wetland DEM Ponding Model - Serial/OpenCL version\t\n'
				       '\n'
				       'Copyright (C) 2010,2012, 2014 Kevin Shook, Centre for Hydrology \n'
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
				       'Developed by Oluwaseun Sharomi and Raymond Spiteri\n'
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
				       'Please choose whether to use serial or OpenCL.\n', 'Error', wx.OK | wx.ICON_ERROR)
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
		
	def Verify(self, event):
		self.button11.Enable(True)
		self.button12.Enable(True)
		self.button19a.Enable(True)
		method = self.combo.GetValue()
		if method=='add':
			self.lblname5.Enable(True)
			self.editname5.Enable(True)
			self.lblname6.Enable(True)
			self.editname6.Enable(True)
			self.lblname7.Enable(True)
			self.editname7.Enable(True)		 
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
			self.txt1.Enable(True)
			self.button11.Enable(True)
			self.txt2.Enable(True)
			self.button12.Enable(True)
			self.txt3.Enable(True)
			#self.button13.Enable(True)
			self.txt4.Enable(True)
			#self.button14.Enable(True)		  
			self.lblname8.Enable(True)
			self.combo8.Enable(True)
			self.button18.Enable(True)
			self.lblname9.Enable(True)
		elif method=='subtract':
			self.lblname5a.Enable(True)
			self.editname5a.Enable(True)
			self.lblname7a.Enable(True)
			self.editname7a.Enable(True)		 
			self.lblname5.Enable(False)
			self.editname5.Enable(False)
			self.lblname6.Enable(False)
			self.editname6.Enable(False)
			self.lblname7.Enable(False)
			self.editname7.Enable(False)
			self.lblname6b.Enable(False)
			self.editname6b.Enable(False)
			self.lblname7b.Enable(False)
			self.editname7b.Enable(False)
			self.lblname9a.Enable(False)
			self.txt9a.Enable(False)
			self.button19a.Enable(False)	
			self.txt1.Enable(True)
			self.button11.Enable(True)
			self.txt2.Enable(True)
			self.button12.Enable(True)
			self.txt3.Enable(True)
			#self.button13.Enable(True)
			self.txt4.Enable(True)
			#self.button14.Enable(True)		  
			self.lblname8.Enable(True)
			self.combo8.Enable(True)
			self.button18.Enable(True)
			self.lblname9.Enable(True)
		elif method=='drain':
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
			self.lblname6b.Enable(True)
			self.editname6b.Enable(True)
			self.lblname7b.Enable(True)
			self.editname7b.Enable(True)
			self.lblname9a.Enable(False)
			self.txt9a.Enable(False)
			self.button19a.Enable(False)			  
			self.txt1.Enable(True)
			self.button11.Enable(True)
			self.txt2.Enable(True)
			self.button12.Enable(True)
			self.txt3.Enable(True)
			#self.button13.Enable(True)
			self.txt4.Enable(True)
			#self.button14.Enable(True)		  
			self.lblname8.Enable(True)
			self.combo8.Enable(True)
			self.button18.Enable(True)
			self.lblname9.Enable(True)
		elif method=='TextFile':
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
			self.lblname9a.Enable(True)
			self.txt9a.Enable(True)
			self.button19a.Enable(True)
			self.txt1.Enable(False)
			self.button11.Enable(False)
			self.txt2.Enable(False)
			self.button12.Enable(False)
			self.txt3.Enable(False)
			#self.button13.Enable(False)
			self.txt4.Enable(False)
			#self.button14.Enable(False)		  
			self.lblname8.Enable(False)
			self.combo8.Enable(False)
			self.button18.Enable(False)
			self.lblname9.Enable(False)
			self.combo9.Enable(False)
		else:
		        self.OnError1()


	def OnErrorDem(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please specify DEM filename/path.\n', 'Error', wx.OK | wx.ICON_ERROR)
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
				       'Please specify NULL if checkpontingPlease specified runoff fraction is not required.\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()
		
	def OnErrorM2(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please choose whether to use CPU or GPU.\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()
		
	def OnErrorElev(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please specify elevation tolerance.\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()

	def OnErrorDrain(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please specify drain tolerance.\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()
		
	def OnErrorFile(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please specify Input filename/path.\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()
		
	def OnErrorDepthS(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please specified depth of water to subtract.\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()
		
	def OnErrorDepthA(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please specified depth of water to add.\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()
		
	def OnErrorRunOff(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'Please specified runoff fraction\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()
		
	def MainError(self):
		dlg = wx.MessageDialog(None, 'WDPM - Error\t\n'
				       '\n'
				       'One or more of the parameters are missing\n', 'Error', wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()

	def OnSimulationFinished(self):
		dlg = wx.MessageDialog(None, 'WDPM\t\n'
				       '\n'
				       'Simulation is not running\n', 'Information', wx.OK | wx.ICON_INFORMATION)
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
		    print("==== Simulation Terminated ====")
		    
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
		if os.path.isfile(reportfilepath)==True:
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

	def Module(self,cmd,cmd2):
		self.clearbutton.Enable(True)
		self.endbutton.Enable(True)
		self.runbutton.Enable(False)
		self.Reportremove()
		reportfilepath=open(os.path.join(self.txt0a.GetValue(),"report.txt"), "w")
		self.process0 = subprocess.Popen(cmd, stdout=reportfilepath, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
		self.thread = threading.Thread(target=self.enqueue_output, args=(cmd2,))
		self.thread.daemon = True
		self.thread.start()

	def Module2(self,cmd):
		self.Reportremove()
		reportfilepath=open(os.path.join(self.txt0a.GetValue(),"report.txt"), "w")
		self.process = subprocess.Popen(cmd, stdout=reportfilepath, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
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
			self.processx = subprocess.Popen(cmd, stdout=reportfilepath, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
		else:
			cmd = ['cmap.bat', self.txt9xa.GetValue()]
			self.processx = subprocess.Popen(cmd, stdout=reportfilepath, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
		self.threadx = threading.Thread(target=self.cmap)
		self.threadx.daemon = True
		self.threadx.start()

	def RunSim(self,event):
		time.sleep(1)
		self.log.Clear()
		self.log.Enable(False)
		self.RunSimulationOptimized()
		#if self.cbs1a.GetValue()==True:
		#    self.RunSimulationOptimized()
		#else:
		#    self.RunSimulation()

	def RunSimulationOptimized(self):
		solver=os.getcwd()+"/WDPMCL"
		solverw=os.getcwd()+"\WDPMCL.exe"
		method = self.combo.GetValue()
		plat = platform.system()
		checkpointfilenamex = os.path.join(self.txt0a.GetValue(),"temp.asc")
		if os.path.isfile(checkpointfilenamex)==True:
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
			   
			if os.path.isfile("self.txt1.GetValue()")==True:
			    pass
			if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue())))==True:
			    pass
			else:
			    print ("DEM file not present. Use the Browse button to locate file.")
			    plat="error"
			   
			if plat=='Darwin' or plat=='Linux':
				if checkpointfilename == "NULL":
					cmd0 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
					       checkpointfilenamex, waterdeptha, runoffrac, elevationtol, method1, method2, "0"]
					cmd1 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
					       checkpointfilenamex, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
					self.Module(cmd0,cmd1)
				else:
					if os.path.isfile(checkpointfilename)==True:
						cmd = [solver, method, demfilename, waterfilename, wateroutputfilename, 
						       checkpointfilename, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
						self.Module2(cmd)
					else:
						cmd0 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
						       checkpointfilename, waterdeptha, runoffrac, elevationtol, method1, method2, "0"]
						cmd1 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
						       checkpointfilename, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
						self.Module(cmd0,cmd1)
			elif plat=='error':
				self.MainError()			     
			else:
				if checkpointfilename == "NULL":
					cmd0 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
					       checkpointfilenamex, waterdeptha, runoffrac, elevationtol, method1, method2, "0"]
					cmd1 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
					       checkpointfilenamex, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
					self.Module(cmd0,cmd1)
				else:
					if os.path.isfile(checkpointfilename)==True:
						cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
						       checkpointfilename, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
						self.Module2(cmd)
					else:
						cmd0 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
						       checkpointfilename, waterdeptha, runoffrac, elevationtol, method1, method2, "0"]
						cmd1 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
						       checkpointfilename, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
						self.Module(cmd0,cmd1)
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
			if method1=="Serial CPU":
			  method1="0"
			elif method1=="OpenCL":
			  method1="1"
			  
			if method2=="GPU":
			  method2="0"
			elif method2=="CPU":
			  method2="1"	

			if os.path.isfile("self.txt1.GetValue()")==True:
			    pass
			if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue())))==True:
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
				if checkpointfilename == "NULL":
					cmd0 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, waterdepths, elevationtol, method1, method2, "0"]
					cmd1 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, waterdepths, elevationtol, method1, method2, "1"]
					self.Module(cmd0,cmd1)
				else:
					if os.path.isfile(checkpointfilename)==True:
						cmd = [solver, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilename, waterdepths, elevationtol, method1, method2,"1"]
						self.Module2(cmd)
					else:
						cmd0 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, waterdepths, elevationtol, method1, method2, "0"]
						cmd1 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, waterdepths, elevationtol, method1, method2, "1"]
						self.Module(cmd0,cmd1)
			elif plat=='error':
				self.MainError()
			else:
				if checkpointfilename == "NULL":
					cmd0 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, waterdepths, elevationtol, method1, method2, "0"]
					cmd1 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, waterdepths, elevationtol, method1, method2, "1"]
					self.Module(cmd0,cmd1)
				else:
					if os.path.isfile(checkpointfilename)==True:
						cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilename, waterdepths, elevationtol, method1, method2,"1"]
						self.Module2(cmd)
					else:
						cmd0 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, waterdepths, elevationtol, method1, method2, "0"]
						cmd1 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, waterdepths, elevationtol, method1, method2, "1"]
						self.Module(cmd0,cmd1)
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
			if method1=="Serial CPU":
			  method1="0"
			elif method1=="OpenCL":
			  method1="1"

			if os.path.isfile("self.txt1.GetValue()")==True:
			    pass
			if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue())))==True:
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
				if checkpointfilename == "NULL":
					cmd0 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, elevationtol, draintol, method1, method2, "0"]
					cmd1 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, elevationtol, draintol, method1, method2, "1"]
					self.Module(cmd0,cmd1)
				else:
					if os.path.isfile(checkpointfilename)==True:
						cmd = [solver, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilename, elevationtol, draintol, method1, method2,"1"]
						self.Module2(cmd)
					else:
						cmd0 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, elevationtol, draintol, method1, method2, "0"]
						cmd1 = [solver, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, elevationtol, draintol, method1, method2, "1"]
						self.Module(cmd0,cmd1)
			elif plat=='error':
				self.MainError()
			else:
				if checkpointfilename == "NULL":
					cmd0 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, elevationtol, draintol, method1, method2, "0"]
					cmd1 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
						checkpointfilenamex, elevationtol, draintol, method1, method2, "1"]
					self.Module(cmd0,cmd1)
				else:
					if os.path.isfile(checkpointfilename)==True:
						cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilename, elevationtol, draintol, method1, method2,"1"]
						self.Module2(cmd)
					else:
						cmd0 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, elevationtol, draintol, method1, method2, "0"]
						cmd1 = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
							checkpointfilenamex, elevationtol, draintol, method1, method2, "1"]
						self.Module(cmd0,cmd1)
		elif method=='TextFile':
			filename = str(self.txt9a.GetValue())
			if filename=='':
				self.OnErrorFile()
			else:
				newfile1 = os.path.join(self.txt0a.GetValue(),"input1.in")
				newfile2 = os.path.join(self.txt0a.GetValue(),"input2.in")
				f = open(filename,'r')
				data_list = f.readlines()
				with open(newfile1, "w") as output:
					for i in range(len(data_list)):
						if i==4:
							if data_list[i].strip()=="NULL":
								checkpointf=os.path.join(self.txt0a.GetValue(),"temp.asc")
								output.write(checkpointf)
								output.write("\n")
						else:
						    output.write(data_list[i])
					output.write("\n")
					output.write("0")
				with open(newfile2, "w") as output:
					for i in range(len(data_list)):
						if i==4:
							if data_list[i].strip()=="NULL":
								checkpointf=os.path.join(self.txt0a.GetValue(),"temp.asc")
								output.write(checkpointf)
								output.write("\n")
						else:
						    output.write(data_list[i])
					output.write("\n")
					output.write("1")
				if plat=='Darwin' or plat=='Linux':
					if data_list[4].strip() == "NULL":
						cmd0 = [solver, newfile1]
						cmd1 = [solver, newfile2]
						self.Module(cmd0,cmd1)
					else:
						if os.path.isfile(data_list[4].strip())==True:
							cmd = [solver, newfile]
							self.Module2(cmd)
						else:
						    cmd0 = [solver, newfile1]
						    cmd1 = [solver, newfile2]
						    self.Module(cmd0,cmd1)
				elif plat=='error':
					self.MainError()
				else:
					if data_list[4].strip() == "NULL":
						cmd0 = [solverw, newfile1]
						cmd1 = [solverw, newfile2]
						self.Module(cmd0,cmd1)
					else:
						if os.path.isfile(data_list[4].strip())==True:
							cmd = [solverw, newfile]
							self.Module2(cmd)
						else:
						    cmd0 = [solverw, newfile1]
						    cmd1 = [solverw, newfile2]
						    self.Module(cmd0,cmd1)


	#def RunSimulation(self):
	#	solver=os.getcwd()+"/WDPMCL"
	#	solverw=os.getcwd()+"\WDPMCL.exe"
	#	method = self.combo.GetValue()
	#	plat = platform.system() 
	#	if method=='add':
	#		demfilename = str(self.txt1.GetValue())
	#		waterfilename = str(self.txt2.GetValue())
	#		wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
	#		checkpointfilenamex = os.path.join(self.txt0a.GetValue(),"temp.asc")
	#		if os.path.isfile(checkpointfilenamex)==True:
	#		    os.remove(checkpointfilenamex)
	#		if self.txt4.GetValue()=='NULL':
	#		   checkpointfilename = str(self.txt4.GetValue())
	#		else:
	#		   checkpointfilename = os.path.join(self.txt0a.GetValue(),str(self.txt4.GetValue()))
	#		method1 = self.combo8.GetValue()
	#		method2 = self.combo9.GetValue()
	#		waterdeptha = str(self.editname5.GetValue()) 
	#		runoffrac = str(self.editname6.GetValue())
	#		elevationtol = str(self.editname7.GetValue())
	#		if method1=="Serial CPU":
	#		  method1="0"
	#		elif method1=="OpenCL":
	#		  method1="1"
	#		  
	#		if method2=="GPU":
	#		  method2="0"
	#		elif method2=="CPU":
	#		  method2="1"	
	#
	#		if demfilename=='':
	#		  self.OnErrorDem()
	#		  plat='error'
	#		if waterfilename=='':
	#		  self.OnErrorWater()
	#		  plat='error'
	#		if wateroutputfilename=='':
	#		  self.OnErrorOutput()
	#		  plat='error'
	#		if checkpointfilename=='':
	#		  self.OnErrorCheckpoint()
	#		  plat='error'
	#		if method1=='':
	#		  self.OnErrorM1()
	#		  plat='error'
	#		if method1=='1':
	#		  if method2=='':
	#		      self.OnErrorM2()
	#		      plat='error'
	#		if elevationtol=='':
	#		   self.OnErrorElev()
	#		   plat='error'
	#		if waterdeptha=='':
	#		   self.OnErrorDepthA()
	#		   plat='error'
	#		if runoffrac=='':
	#		   self.OnErrorRunOff()
	#		   plat='error'
	#		   
	#		if os.path.isfile("self.txt1.GetValue()")==True:
	#		    pass
	#		if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue())))==True:
	#		    pass
	#		else:
	#		    print "DEM file not present. Use the Browse button to locate file."
	#		    plat="error"
	#		   
	#		if plat=='Darwin' or plat=='Linux':
	#			cmd = [solver, method, demfilename, waterfilename, wateroutputfilename, 
	#			       checkpointfilename, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
	#			self.Module2(cmd)
	#		elif plat=='error':
	#			self.MainError()			     
	#		else:
	#			cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
	#				checkpointfilenamex, waterdeptha, runoffrac, elevationtol, method1, method2, "1"]
	#			self.Module2(cmd)
	#	elif method=='subtract':
	#		demfilename = str(self.txt1.GetValue())
	#		waterfilename = str(self.txt2.GetValue())
	#		wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
	#		if self.txt4.GetValue()=='NULL':
	#		   checkpointfilename = str(self.txt4.GetValue())
	#		else:
	#		   checkpointfilename = os.path.join(self.txt0a.GetValue(),str(self.txt4.GetValue()))
	#		method1 = self.combo8.GetValue()
	#		method2 = self.combo9.GetValue()  
	#		waterdepths = str(self.editname5a.GetValue())
	#		elevationtol = str(self.editname7a.GetValue())
	#		if method1=="Serial CPU":
	#		  method1="0"
	#		elif method1=="OpenCL":
	#		  method1="1"
	#		  
	#		if method2=="GPU":
	#		  method2="0"
	#		elif method2=="CPU":
	#		  method2="1"	
	#
	#		if os.path.isfile("self.txt1.GetValue()")==True:
	#		    pass
	#		if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue())))==True:
	#		    pass
	#		else:
	#		    print "DEM file not present. Use the Browse button to locate file."
	#		    plat="error"
	#
	#		if demfilename=='':
	#		  self.OnErrorDem()
	#		  plat='error'
	#		if waterfilename=='':
	#		  self.OnErrorWater()
	#		  plat='error'
	#		if wateroutputfilename=='':
	#		  self.OnErrorOutput()
	#		  plat='error'
	#		if checkpointfilename=='':
	#		  self.OnErrorCheckpoint()
	#		  plat='error'
	#		if method1=='':
	#		  self.OnErrorM1()
	#		  plat='error'
	#		if method1=='1':
	#		  if method2=='':
	#		      self.OnErrorM2()
	#		      plat='error'
	#		if elevationtol=='':
	#		   self.OnErrorElev()
	#		   plat='error'
	#		if waterdepths=='':
	#		   self.OnErrorDepthS()
	#		   plat='error'
	#		if plat=='Darwin' or plat=='Linux':
	#			cmd = [solver, method, demfilename, waterfilename, wateroutputfilename, 
	#			       checkpointfilename, waterdepths, elevationtol, method1, method2, "1"]
	#			self.Module2(cmd)
	#		elif plat=='error':
	#			self.MainError()
	#		else:
	#			cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
	#			       checkpointfilename, waterdepths, elevationtol, method1, method2, "1"]
	#			self.Module2(cmd)
	#	elif method=='drain':
	#		demfilename = str(self.txt1.GetValue())
	#		waterfilename = str(self.txt2.GetValue())
	#		wateroutputfilename = os.path.join(self.txt0a.GetValue(),str(self.txt3.GetValue()))
	#		if self.txt4.GetValue()=='NULL':
	#		   checkpointfilename = str(self.txt4.GetValue())
	#		else:
	#		   checkpointfilename = os.path.join(self.txt0a.GetValue(),str(self.txt4.GetValue()))
	#		method1 = self.combo8.GetValue()
	#		method2 = self.combo9.GetValue()
	#		draintol = str(self.editname6b.GetValue())
	#		elevationtol = str(self.editname7b.GetValue())
	#		if method1=="Serial CPU":
	#		  method1="0"
	#		elif method1=="OpenCL":
	#		  method1="1"
	#
	#		if os.path.isfile("self.txt1.GetValue()")==True:
	#		    pass
	#		if os.path.isfile(os.path.join(self.txt0a.GetValue(),str(self.txt1.GetValue())))==True:
	#		    pass
	#		else:
	#		    print "DEM file not present. Use the Browse button to locate file."
	#		    plat="error"
	#
	#		if method2=="GPU":
	#		  method2="0"
	#		elif method2=="CPU":
	#		  method2="1"	
	#
	#		if demfilename=='':
	#		  self.OnErrorDem()
	#		  plat='error'
	#		if waterfilename=='':
	#		  self.OnErrorWater()
	#		  plat='error'
	#		if wateroutputfilename=='':
	#		  self.OnErrorOutput()
	#		  plat='error'
	#		if checkpointfilename=='':
	#		  self.OnErrorCheckpoint()
	#		if method1=='':
	#		  self.OnErrorM1()
	#		  plat='error'
	#		if method1=='1':
	#		  if method2=='':
	#		      self.OnErrorM2()
	#		      plat='error'
	#		if elevationtol=='':
	#		   self.OnErrorElev()
	#		   plat='error'
	#		if draintol=='':
	#		   self.OnErrorDrain()
	#		   plat='error'
	#		if plat=='Darwin' or plat=='Linux':
	#			cmd = [solver, method, demfilename, waterfilename, wateroutputfilename, 
	#			       checkpointfilename, elevationtol, draintol, method1, method2, "1"]
	#			self.Module2(cmd)
	#		elif plat=='error':
	#			self.MainError()
	#		else:
	#			cmd = [solverw, method, demfilename, waterfilename, wateroutputfilename, 
	#			       checkpointfilename, elevationtol, draintol, method1, method2, "1"]
	#			self.Module2(cmd)
	#	elif method=='TextFile':
	#		filename = str(self.txt9a.GetValue())
	#		if filename=='':
	#			self.OnErrorFile()
	#		else:
	#			newfile = os.path.join(self.txt0a.GetValue(),"input.in")
	#			f = open(filename,'r')
	#			data_list = f.readlines()
	#			with open(newfile, "w") as output:
	#				for i in range(len(data_list)):
	#					    output.write(data_list[i])
	#				output.write("\n")
	#				output.write("1")
	#			if plat=='Darwin' or plat=='Linux':
	#				cmd = [solver, newfile]
	#				self.Module2(cmd)
	#			elif plat=='error':
	#				self.MainError()
	#			else:
	#				cmd = [solver, newfile]
	#				self.Module2(cmd)

	def EndSimulation(self, event):
		if self.flagz == 1:
		    self.OnSimulationClose()
		else:
		    self.Destroy()
		

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

	def OnOpen1(self,event):
		self.dirname1 = ''
		dlg = wx.FileDialog(self, "Choose a file", self.dirname1,"", "*.asc", wx.FD_OPEN)   
		if dlg.ShowModal()==wx.ID_OK:
			self.filename1=dlg.GetFilename()
			self.dirname1=dlg.GetPath()
			self.txt1.Clear() 
			self.txt1.write(self.dirname1)
		dlg.Destroy()

	def OnOpen2(self,event):
		self.dirname2 = ''
		dlg = wx.FileDialog(self, "Choose a file", self.dirname2,"", "*.asc", wx.FD_OPEN)     
		if dlg.ShowModal()==wx.ID_OK:
			    self.filename2=dlg.GetFilename()
			    self.dirname2=dlg.GetPath()
			    self.txt2.Clear()
			    self.txt2.write(self.dirname2)
		dlg.Destroy()	
		
	def OnOpen3(self,event):
		self.dirname3 = ''
		dlg = wx.FileDialog(self, "Choose a file", self.dirname3,"", "*.asc", wx.FD_OPEN)     
		if dlg.ShowModal()==wx.ID_OK:
			self.filename3=dlg.GetFilename()
			self.dirname3=dlg.GetPath()
			self.txt3.Clear()
			self.txt3.write(self.dirname3)
		dlg.Destroy()
		
	def OnOpen4(self,event):
		self.dirname4 = ''
		dlg = wx.FileDialog(self, "Choose a file", self.dirname4,"", "*.asc", wx.FD_OPEN)     
		if dlg.ShowModal()==wx.ID_OK:
			self.filename4=dlg.GetFilename()
			self.dirname4=dlg.GetPath()
			self.txt4.Clear()
			self.txt4.write(self.dirname4)
		dlg.Destroy()
		
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
  app=wx.PySimpleApp(redirect=False)
  frame=Size(parent=None,id_=-1)
  frame.Show()
  app.MainLoop()
