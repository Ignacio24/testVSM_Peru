# -*- coding: utf-8 -*-

#MxH_Helmholtz_AGFM

import numpy
import time
import magdynlab.instruments
import magdynlab.controlers
import magdynlab.data_types
import threading_decorators as ThD
import matplotlib.pyplot as plt

@ThD.gui_safe
def MyPlot(Data):
    f = plt.figure('VSM MxH', (5,4))
    
    if not(f.axes):
        plt.subplot() 
    ax = f.axes[0]
    #ax.clear()
    if not(ax.lines):
        ax.plot([],[],'b.-')
        ax.set_xlim(*Data.xlim)
        ax.set_ylim(*Data.ylim)
    line = ax.lines[-1]
    line.set_data(Data.X, Data.Y)
    ax.set_xlabel('Field (Oe)')
    ax.set_ylabel('m')
    ax.grid(True)

    f.tight_layout()
    f.canvas.draw()
    f.savefig('MxH_%s.png' %time.strftime("%y-%m-%d-%H:%H"))

@ThD.gui_safe
def MyPlot_2(Data):
    #     
    # To plot Field - Time relation
    # Added by Aldo Arriola
    f = plt.figure('VSM H x t', (5,4))
    
    if not(f.axes):
        plt.subplot() 
    ax = f.axes[0]
    #ax.clear()
    if not(ax.lines):
        ax.plot([],[],'b.-')
        #ax.set_xlim(*Data.xlim)
        ax.set_ylim(*Data.ylim)
    line = ax.lines[-1]
    line.set_data(Data.X, Data.Y)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Field (Oe)')
    ax.grid(True)

    f.tight_layout()
    f.canvas.draw()
    f.savefig('Hxt_%s.png' %time.strftime("%y-%m-%d-%H:%H"))

@ThD.gui_safe
def Plot_HxI(Data):
    #     
    # To plot Field - Current (I) relation
    # Added by Aldo Arriola
    f = plt.figure('VSM H x I', (5,4))
    
    if not(f.axes):
        plt.subplot() 
    ax = f.axes[0]
    #ax.clear()
    if not(ax.lines):
        ax.plot([],[],'b.-')
        #ax.set_xlim(*Data.xlim)
        ax.set_ylim(*Data.ylim)
    line = ax.lines[-1]
    line.set_data(Data.X, Data.Y)
    ax.set_xlabel('I (A)')
    ax.set_ylabel('H (Oe)')
    ax.grid(True)

    f.tight_layout()
    f.canvas.draw()
    f.savefig('HxI_%s.png' %time.strftime("%y-%m-%d-%H:%M"))

@ThD.gui_safe
def FreqPlot(Data):
    f = plt.figure('VSM Amp vs Freq', (5,4))
    
    if not(f.axes):
        plt.subplot()
    ax = f.axes[0]
    #ax.clear()
    if not(ax.lines):
        ax.plot([],[],'b.-')
        ax.set_xlim(*Data.xlim)
        ax.set_ylim(*Data.ylim)
    line = ax.lines[-1]
    line.set_data(Data.X, Data.Y)
    ax.set_xlabel('Freq')
    ax.set_ylabel('Amp')
    ax.grid(True)

    f.tight_layout()
    f.canvas.draw()
    f.savefig('MxF.png')
    
class MxH(object):
    def __init__(self):
        logFile = 'C:/VMS_log.log'
        dir_Kepco = 'TCPIP0::192.168.1.8::5025::SOCKET'
        dir_LockIn = 'TCPIP0::192.168.1.4::1234::SOCKET'
        dir_SourceMeter = 'TCPIP0::192.168.1.5::1234::SOCKET'
        PowerSource = magdynlab.instruments.KEPCO_BOP(ResourceName = dir_Kepco)
        LockIn = magdynlab.instruments.SRS_SR830(ResourceName = dir_LockIn)
        SourceMeter = magdynlab.instruments.KEITHLEY_2400(ResourceName = dir_SourceMeter)

        class virtual_voltmeter(object):
            def __init__(self, SourceMeter):
                self.SourceMeter = SourceMeter
                self.SourceMeter.sense_mode = '2-Wires' 
                self.SourceMeter.source_function = 'I'
                self.SourceMeter.source_value = 0
                self.SourceMeter.sense_function = 'V'
                self.SourceMeter.output = 'ON'
            @property
            def voltage(self):
                return self.SourceMeter.sense_value
    
        Voltmeter = virtual_voltmeter(SourceMeter)

        self.VC = magdynlab.controlers.LockIn_Mag_Controler(LockIn)
        self.FC = magdynlab.controlers.FieldControlerDriven(PowerSource, Voltmeter)
        self.FC.Kepco.voltage = 50

        #This is used to plot
        self.Data = magdynlab.data_types.Data2D()
        self.DataFreq = magdynlab.data_types.Data2D()
        ####
        self.msg = "holamundo"
        
    def _SaveData(self, file_name):
        self.Data.save(file_name)

    def PlotData(self, i = None):
        MyPlot(self.Data)

    def PlotFreq(self):
        FreqPlot(self.DataFreq)

    @ThD.as_thread
    def FreqCurve(self, crvf = [], file_name = None, TurnOff = False):
        freqs = numpy.asarray(crvf)

        #Initialize data objects
        self.DataFreq.reset()
        self.DataFreq.xlim = [freqs.min(), freqs.max()]
        sen = self.VC.LockIn.SEN * 1.5 * self.VC.emu_per_V
        self.DataFreq.ylim = [0, sen]
        
        #Loop for each field
        for i, f in enumerate(freqs):
            self.VC.LockIn.setOscilatorFreq(f)
            #time.sleep(0.5)
            a = self.VC.getAmplitude() 
            if a >= 0.9 * self.VC.LockIn.SEN:
                self.VC.LockIn.SEN = 3*self.VC.LockIn.SEN
                a = self.VC.getAmplitude() 
            self.DataFreq.addPoint(f, a*self.VC.emu_per_V)
            FreqPlot(self.DataFreq)
            ThD.check_stop()
            
        if file_name is not None:
            self._SaveData(file_name)
        if TurnOff:
            self.FC.TurnOff()
        self.FC.Kepco.BEEP()

    @ThD.as_thread
    def Measure(self, crv = [], file_name = None, meas_opts = [10, 1, 0.1]):
        fields = numpy.asarray(crv)
        
        # Initialize data objects
        self.Data.reset()
        self.Data.xlim = [fields.min(), fields.max()]
        sen = self.VC.LockIn.SEN * 1.5 * self.VC.emu_per_V
        self.Data.ylim = [-sen, sen]
        
        n_pts, iniDelay, measDelay = meas_opts
        
        # Loop for each field
        for i, h in enumerate(fields):
            self.FC.setField(h)
            while abs(h - self.FC.getField()) > 50:
                self.FC.setField(h)
            #time.sleep(0.5)
            m, sm = self.VC.getMagnetization(n = n_pts, iniDelay = iniDelay, measDelay = measDelay)
            self.Data.addPoint(h, m)
            MyPlot(self.Data)
            ThD.check_stop()
            
        if file_name != None:
            self._SaveData(file_name)
        self.FC.TurnOff()
        self.FC.Kepco.BEEP()

    def Stop(self, TurnOff = True):
        print('Stoping...')
        self.FC.BEEP()
        self.Measure.Stop()
        self.FreqCurve.Stop()
        if self.Measure.thread is not None:
            self.Measure.thread.join()
        if self.FreqCurve.thread is not None:
            self.FreqCurve.thread.join()
        print('DONE')
        time.sleep(1)
        self.FC.BEEP()
        time.sleep(0.1)
        self.FC.BEEP()
        if TurnOff:
            print('Turning field OFF')
            self.FC.setField(0)
            print('DONE')

#####################################################
# Testing SetField.                                 #
# Added by Aldo Arriola                             #
# To evaluate the realtionship time-Field-change    #
#####################################################
  

    def test_setField(self, field):
       
        global t0

        [tu,fu, tt] = self.FC.test_setField(field)
        #[td,fd] = self.FC.test_setField(field)
        #t = tu + td
        t0=tt
        fig, ax = plt.subplots()
        ax.plot(tu,fu, 'r.-')
        ax.set_xlabel('time (s)')
        ax.set_ylabel('Field (Oe)')
        ax.set_title('test setField')
        plt.show()
        #print(self.msg)

    def test_setField_HxI(self, field):
       
        global t0

        [tu,fu, tt, iu] = self.FC.test_setField_HxI(field)
        #[td,fd] = self.FC.test_setField(field)
        #t = tu + td
        t0=tt
        fig, ax = plt.subplots()
        ax.plot(iu,fu, 'r.-')
        ax.set_xlabel('I ()')
        ax.set_ylabel('Field (Oe)')
        ax.set_title('test setField HxI')
        plt.show()
        #print(self.msg)

    @ThD.as_thread
    def test_Measure(self, crv = [], file_name = None, meas_opts = [10, 1, 0.1]):
        
        global t0 

        fields = numpy.asarray(crv)
        print("Field cicle for histeresys")
        # Initialize data objects
        self.Data.reset()
        self.Data.ylim = [fields.min(), fields.max()]
        sen = self.VC.LockIn.SEN * 1.5 * self.VC.emu_per_V
        #self.Data.ylim = [-sen, sen]
        
        n_pts, iniDelay, measDelay = meas_opts
        
        # Loop for each field
        for i, h in enumerate(fields):
            self.FC.setField(h)
            while abs(h - self.FC.getField(delay=0)) > 30:
                self.FC.setField(h)
            f = self.FC.getField(delay=0)
            t = time.time() - t0
            print(t, '\t', f)
            #time.sleep(0.5)
            #m, sm = self.VC.getMagnetization(n = n_pts, iniDelay = iniDelay, measDelay = measDelay)
            self.Data.addPoint(t, f)
            MyPlot_2(self.Data)
            ThD.check_stop()
        print ("Time elapsed: %f min" %((time.time() - t0)/60))
        if file_name != None:
            self._SaveData(file_name)
        self.FC.TurnOff()
        self.FC.Kepco.BEEP()


    @ThD.as_thread
    def test_Measure_HxI(self, crv = [], file_name = None, meas_opts = [10, 1, 0.1]):
        # To measure H vs I 
        global t0 

        fields = numpy.asarray(crv)
        print("Field cicle for histeresys\nEvaluating HxI")
        # Initialize data objects
        self.Data.reset()
        self.Data.ylim = [fields.min(), fields.max()]
        sen = self.VC.LockIn.SEN * 1.5 * self.VC.emu_per_V
        #self.Data.ylim = [-sen, sen]
        
        n_pts, iniDelay, measDelay = meas_opts
        
        # Loop for each field
        for i, h in enumerate(fields):
            self.FC.setField(h)
            
            while abs(h - self.FC.getField(delay=0)) > 30:
                self.FC.setField(h)
            
            f = self.FC.getField(delay=0)
            t = time.time() - t0
            c = self.FC.getCurrent()

            print(t, '\t', f, '\t', c)
            #time.sleep(0.5)
            #m, sm = self.VC.getMagnetization(n = n_pts, iniDelay = iniDelay, measDelay = measDelay)
            self.Data.addPoint(c, f)
            Plot_HxI(self.Data)
            ThD.check_stop()
        print ("Time elapsed: %f min" %((time.time() - t0)/60))
        if file_name != None:
            self._SaveData(file_name)
        self.FC.TurnOff()
        self.FC.Kepco.BEEP()