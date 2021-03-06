'''
    author: Cody Roberson
    date: 1/13/2020
    description: This is the main executable for the readout software. Here, we use the keithley and cryocon interfaces to gather our data
    and plot it.
    Based off of an example from https://matplotlib.org/3.1.1/gallery/user_interfaces/embedding_in_qt_sgskip.html
'''

import sys
import time
import os
import numpy as np
import keithley
import cryocon
import time
import matplotlib
####################################### CONFIG ############################################
cryoconPort = "COM8"
keithleyPort = "COM4"
###########################################################################################

from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure


def init_cryocon():
    return cryocon.Cryocon(cryoconPort)


def init_keithley():
    dev_keith = keithley.Keithley2400LV(keithleyPort, False)
    dev_keith.openPort()
    dev_keith.initResistanceMeasurement()
    dev_keith.setSourceCurrent(1e-5) # 1.0e-7 For Nanos
    dev_keith.turnOutput_ON()
    return dev_keith

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        # Ask user for filename to save data to
        self.filename = QtWidgets.QFileDialog.getSaveFileName(self, "Save Measurement Data", "", "data csv (*.csv)")
        if self.filename == ("",""):
            self.filename = "cryoreadout_dat_{}.csv".format(time.time())
        else:
            self.filename = self.filename[0] + ".csv"
        print("[CRYOREADOUT] save file set to {}".format(self.filename))
        
        # Open data file
        self.dfHandle = None
        try:
            self.dfHandle = open(self.filename, 'w')
        except IOError:
            print("[CRYOREADOUT] ERROR: Can't save to selected file or path")
            exit()
        
        # init devices
        self.cryo = init_cryocon()
        self.keith = init_keithley()
        self.times = []
        self.temps = []
        self.temps2 = []
        self.resistances = []


        # Create and add canvas + figure to the qt widget
        restemp_canvas = FigureCanvas(Figure(figsize=(14, 8)))
        layout.addWidget(restemp_canvas)
        self.addToolBar(QtCore.Qt.BottomToolBarArea,
                        NavigationToolbar(restemp_canvas, self))
        tcanvas = FigureCanvas(Figure(figsize=(14, 8)))
        layout.addWidget(tcanvas)
        self.addToolBar(QtCore.Qt.BottomToolBarArea,
                        NavigationToolbar(tcanvas, self))

        self._restempPlot = restemp_canvas.figure.subplots()
        self._tempPlot = tcanvas.figure.subplots()
        self._timer = restemp_canvas.new_timer(
            1250, [(self._update_canvas, (), {})])
        self._timer.start()

    def _update_canvas(self):
        self._restempPlot.clear()
        self._tempPlot.clear()
        self._restempPlot.set_xlabel("Temperature (K)")
        self._restempPlot.set_ylabel("Resistance (Ohms)")
        self._tempPlot.set_xlabel("Time (Seconds)")
        self._tempPlot.set_ylabel("Temperature (K)")
        
        # Get resistance and add to list
        bytestring = self.keith.getMeasermentResistance()
        resistance = 0
        try:
            resistance = float(bytestring[29:41])
        except ValueError:
            print("[CRYOREADOUT] Something went wrong when attempting to convert response to values. Perhaps the connection is invalid?")
            print("Try closing the IPython Kernel and swapping the ports.")
            self._timer.stop()
            self.close()
            return

        self.resistances.append(resistance)
        
        # Get temperature and add to list
        tempr = self.cryo.getTemperatures()
        self.temps.append(tempr[0])
        self.temps2.append(tempr[1])
        currentTime = time.time()
        self.times.append(currentTime)
        # save data as time, resistance, temperature
        self.dfHandle.write("{},{},{}\n".format(time.time(), resistance, tempr[0]))
        print ("{},{},{},{}\n".format(time.time(), resistance, tempr[0], tempr[1]))
        self.dfHandle.flush()

        # draw plot
        self._restempPlot.plot(self.temps, self.resistances)
        self._tempPlot.plot(self.times, self.temps, 'r', self.times, self.temps2, 'b')
        self._restempPlot.figure.canvas.draw()
        self._tempPlot.figure.canvas.draw()

    
    def closeup(self):
        self.cryo.closeConnection()
        self.keith.turnOutput_OFF()
        self.keith.closePort()
        self.dfHandle.close()
        print("Done")



if __name__ == "__main__":
    qapp = QtWidgets.QApplication(sys.argv)
    app = ApplicationWindow()
    app.show()
    qapp.exec_()
    app.closeup()