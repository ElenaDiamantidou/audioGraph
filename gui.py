from __future__ import unicode_literals
import sys
import os
import os.path
import random
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor

matplotlib.use('Qt5Agg')
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QFile, QIODevice, QObject, QRect
from PyQt5.QtMultimedia import (QMediaContent,
        QMediaMetaData, QMediaPlayer, QMediaPlaylist, QAudioOutput, QAudioFormat)
from PyQt5.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QPushButton,
        QSizePolicy, QVBoxLayout, QWidget, QToolTip, QLabel, QFrame, QGridLayout, QMenu, qApp, QLineEdit)


from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.transforms as transforms
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm

from numpy import arange, sin, pi

import wave
import numpy as np
import subprocess
import csv
import cv2
from pyAudioAnalysis import audioFeatureExtraction as aF
from pyAudioAnalysis import audioSegmentation as aS
from pyAudioAnalysis import audioBasicIO


#a few globals...

#Argument files
wavFileName = None
rosbagName = None

#audio signal
spf = 0
duration = 0
signal = 0

#variables for start-end time, get mouse clicks and play
xStart = 0
xEnd = 0
startTimeToPlay = 0
endTimeToPlay = 0

#Clicks variables
counterClick = 1

#Waveform and Gantt Chart figures for widgets and plot
fig = None
chartFig = None

#Player flags for QtMultimedia player options
playerStarted = False
durationFlag = 0
xPos = 0
yPos = 100

#Annotation colors
colorName = None
annotationColors = (['Speech', 'green'],['Music','red'], ['Activity', 'magenta'],['Laugh', 'yellow'], ['Cough', '#4B0082'])
#list of green shades
GreenShades = ['#007300', '#00e500','#006600','#007f00','#005900','#00cc00','#004c00', '#004000', '#009900', '#003300', '#00b200', '#002600']
shadesAndSpeaker = []
greenIndex = 0

#Annotations important variables
classLabels = ['Music', 'Activity', 'Laugh', 'Cough']
annotationFlag = False
annotations = []
isBold = False
isDeleted = False
checkYaxis = False
xTicks = []
text_ = None
overlap = False
text1, text2 = None,None
selected = False
xCheck = None
isAbove = False

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  ONCLICK FUNCTION                                                                       #
#  count clicks on Waveform                                                               #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def onclick(event):

    global xStart, xEnd, startTimeToPlay, endTimeToPlay
    global counterClick
    global wavFileName, fig
    global playerStarted, durationFlag
    global xPos, yPos
    global annotationFlag, isBold, isDeleted, selected, xCheck, isDeleted

    tempPass = False
    flagDraw = True
    color = 'turquoise'

    if event.xdata != None:

        #Left Mouse Click -> select audio segment\
        #----------------------
        if event.button == Qt.LeftButton:
            # >> Get Clicks for Start-End Time...
            x = event.xdata
            # >> Clear axes...
            fig.clear()

            # >> First Click
            if counterClick == 1:
                xStart = x*1000
                print 'Start time %f ms' %xStart      
                durationFlag = 1
                if annotationFlag == True:
                    tempPass = True
                    annotationFlag = False
                
                playerStarted = False
                
                # >> Start not out of waveform bounds
                if xStart < 0:
                    xStart = 0
                    print '-> Correction time %f ms' %xStart

            # >> Second Click
            if counterClick == 2 and tempPass == False:
                if isBold:
                    isBold = False
                    durationFlag = 0
                    fig.clear()
                else:
                    xEnd = x*1000
                    print 'End Time %f ms' %xEnd
                    durationFlag = 2
                    #check xStart < xEnd
                    if xStart > xEnd:
                        temp = xStart
                        xStart = xEnd
                        xEnd = temp
                        print '  '
                        print 'SWAP START-END TIME'
                        print '-------------'
                        print 'Start Time %f ms' %xStart
                        print 'End Time %f ms' %xEnd
                        print '-------------'
                playerStarted = False


            startTimeToPlay = xStart
            endTimeToPlay = xEnd

            
            counterClick = counterClick + 1
            playFlag = False
            fig.drawCursor(xStart, xEnd, color, playFlag)
            fig.draw()
        else:
            #get mouse coords to specify delete widget position
            #----------------------
            xPos = event.x
            xCheck = event.xdata
            xCheck = xCheck * 1000

            fig.clear()
            #Check for existing annotation
            print '=========================='
            print 'Selected segment'
            if not selected:
                for index in range(len(annotations)):
                    if xCheck >= annotations[index][0] and xCheck <= annotations[index][1]:
                        startTimeToPlay = annotations[index][0]
                        endTimeToPlay = annotations[index][1]
                        for colorIndex in range(len(annotationColors)):
                            if annotationColors[colorIndex][0] == annotations[index][2]:
                                color = annotationColors[colorIndex][1]
            
                            elif annotations[index][2][:8] == 'Speech::':
                                for shadeIndex in range(len(shadesAndSpeaker)):
                                    if annotations[index][2] == shadesAndSpeaker[shadeIndex][0]:
                                        color = shadesAndSpeaker[shadeIndex][1]

                tempPass = True
                durationFlag = 2
                playFlag = False
                playerStarted = False
                fig.drawCursor(startTimeToPlay, endTimeToPlay, color, playFlag)
                #fig.draw()
            else:
                tempPass = True
                durationFlag = 2
                counterClick = counterClick + 1
                playFlag = False
                fig.drawCursor(startTimeToPlay, endTimeToPlay, color, playFlag)
                #fig.draw()
                selected = False

            xS = startTimeToPlay
            xE = endTimeToPlay

            print 'Start time %f ms' %xS 
            print 'End time %f ms' %xE 
            print '=========================='
            #check for selected segment
            if xCheck >= xS and xCheck <= xE:
                fig.drawBold(color)
                fig.draw()
                fig.annotationMenu()
                fig.draw()


class ChartWindow(FigureCanvas):
    global wavFileName, bagfile
    global xStart
    global xEnd
    global annotationFlag, annotations

    def __init__(self, parent=None, width=15, height=1, dpi=100):
        figChart = Figure(figsize=(width, height), dpi=dpi)
        self.axes = figChart.add_subplot(111)

        self.drawChart()

        FigureCanvas.__init__(self, figChart)
        #self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def drawChart(self):
        pass

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  GANTTCHART PLOT FUNCTION                                                               #
#  called from application window                                                         #
#  draw annotations in Ganttchart                                                         #
#  not clickable window                                                                   #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class Chart(ChartWindow):

    labels = []
    classesToPlot = []
    tickY=[]
    tickX=[]
    timeArrayToPlot = []
    c = None
    length = 0
    fileExist = False

    # >> PLOT GANTTCHART
    def drawChart(self):
        global duration
        global colorName
        global annotations, annotationColors
        global checkYaxis, xTicks

        self.classesToPlot = []
        self.labels = []
        self.tickY = []
        self.tickX = []

        #find annotations classes and save them for plot
        #----------------------
        for index1 in range(len(annotations)):
            self.labels.append(annotations[index1][2])

        #remove duplicates
        self.classesToPlot = list(set(self.labels))

        #sort classesToPlot list alphabetically
        self.classesToPlot = sorted(self.classesToPlot)
        self.length = len(self.classesToPlot)


        #Create y and x ticks
        for index in range(self.length):
            self.tickY.append(index + 1)

        for index in range(len(self.timeArrayToPlot)):
            self.tickX.append(index + 1)


        self.axes.hlines(0,0,0)
        #create object to plot
        for index in range(self.length):
            for anIndex in range(len(annotations)):
                if self.classesToPlot[index] == annotations[anIndex][2]:
                    for colorIndex in range(len(annotationColors)):
                        if annotationColors[colorIndex][0] == annotations[anIndex][2]:
                            self.c = annotationColors[colorIndex][1]
                        elif annotations[anIndex][2][:8] == 'Speech::':
                            if len(shadesAndSpeaker) > 0:
                                for shadeIndex in range(len(shadesAndSpeaker)):
                                    if annotations[anIndex][2] == shadesAndSpeaker[shadeIndex][0]:
                                        self.c = shadesAndSpeaker[shadeIndex][1]
                            else:
                                self.c = GreenShades[greenIndex]
                                if greenIndex >= len(GreenShades):
                                    greenIndex = 0
                                else:
                                    greenIndex = greenIndex + 1
                    self.axes.hlines(index + 1, (annotations[anIndex][0]/1000), (annotations[anIndex][1]/1000),linewidth=10, color=self.c)
            self.axes.hlines(index + 2,0,0)

        #Reverse Y axes once
        if checkYaxis == False:
            self.axes.invert_yaxis()
            checkYaxis = True

        #Small Font in Y Axes
        for tick in self.axes.yaxis.get_major_ticks():
            tick.label.set_fontsize(9) 

        self.axes.xaxis.tick_top()
        self.axes.set_xticks(xTicks)
        self.axes.set_xticklabels([])
        self.axes.set_xlim([-1,duration + 1])
        self.axes.set_yticks(self.tickY)
        self.axes.set_yticklabels(self.classesToPlot)
        self.axes.grid(True)


class Window(FigureCanvas):
    global wavFileName, bagfile
    global xStart
    global xEnd
    global annotationFlag, annotations, shadesAndSpeaker, greenIndex

    def __init__(self, parent=None, width=15, height=2, dpi=100):
        global xStart, fig
        global annotationFlag, annotations, bagFile, greenIndex, shadesAndSpeaker, GreenShades

        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)

        self.drawWave()
        self.drawAnnotations()

        FigureCanvas.__init__(self, fig)
        #self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        clickID = fig.canvas.mpl_connect('button_press_event', onclick)
        #clickID = fig.canvas.mpl_connect('motion_notify_event', onmotion)

    def drawWave(self):
        pass

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  POP UP WINDOW                                                                          #
#  called from WAVEFORM                                                                   #
#  open new window to add new speakers                                                    #
#  click "OK" only in completed edit box                                                  #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class MyPopup(QWidget):
    def __init__(self):
        global text_
        global fig, chartFig

        QWidget.__init__(self)
        self.setWindowTitle('Add new Speaker')
        self.main_widget = QtWidgets.QWidget(self)
        self.speakerID = QLineEdit(self)
        self.Ok = QPushButton("Ok", self)
        #self.show()

    # Draw new Speaker window
    #----------------------
    def paintEvent(self, e):
        self.speakerID.setPlaceholderText('Speaker...')
        self.speakerID.setMinimumWidth(100)
        self.speakerID.setEnabled(True)

        self.speakerID.move(90, 15)
        self.Ok.move(115, 60)

        self.speakerID.textChanged.connect(self.speakerLabel)
        self.Ok.clicked.connect(self.closeSpeaker)

        self.Ok.show()
        self.speakerID.show()

    def speakerLabel(self,text):
        global text_
        text_ = 'Speech::' + text 

    # Close and save new Speaker ID
    #----------------------
    def closeSpeaker(self):
        global text_
        global fig, chartFig
        if text_ != 'Add New Speaker':
            text_ = 'Speech::' + self.speakerID.text()
            self.Ok.clicked.disconnect() 
            self.close()

            fig.saveAnnotation()
            fig.draw()
            chartFig.axes.clear()
            chartFig.drawChart()
            chartFig.draw()

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  WAVEFORM PLOT FUNCTION                                                                 #
#  called from application window                                                         #
#  draw signal and annotations                                                            #
#  initialize deletion and choice annotation menu                                         #
#  save annotations in .csv file                                                          #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class Waveform(Window):
    global wavFileName, bagFile
    global xStart, xEnd
    global duration, counterClick, durationFlag, playerStarted
    global colorName, text_, annotationColors
    global rightClick
    global annotations, annotationFlag, isBold, isDeleted
    global greenIndex, GreenShades, shadesAndSpeaker
    global fig, chartFig, x

    # >> CLEAR PLOTS AND RE-DRAW CHANGES
    #----------------------
    def clear(self):
        global counterClick, isDeleted, isBold, xTicks

        self.axes.clear()
        self.drawWave()
        self.drawAnnotations()
        self.draw()

    # >> PLOT WAVEFORM
    #----------------------
    def drawWave(self):
        global duration
        global colorName, xTicks, spf, signal

        #PLOT WAVEFORM
        self.plotStep = 100
        self.signalToPlot = signal[0:-1:self.plotStep]

        self.timeArray = np.arange(0,signal.shape[0] / 16000.0, 1.0/16000)
        self.timeArrayToPlot = self.timeArray[0:-1:self.plotStep]

        #Plot Waveform Signal
        self.axes.plot(self.timeArrayToPlot, self.signalToPlot)
        self.axes.set_yticklabels([])
        self.axes.set_xlim([-1,duration + 1])
        xTicks =  self.axes.get_xticks()
        self.axes.grid(True)

    # >> PLOT CURSORS AND SELECTED AREA
    #----------------------
    def drawCursor(self,start, end, c, playFlag):
        global counterClick, durationFlag, playerStarted, tempPass
        #Media player variables
        global startTimeToPlay, endTimeToPlay, xStart, xEnd
        global isDeleted, isBold
        global selected

        tStart = float(start)/1000.0
        tEnd = float(end)/1000.0
        iS = np.argmin(np.abs(self.timeArrayToPlot - tStart))
        iE = np.argmin(np.abs(self.timeArrayToPlot - tEnd))
        #Draw Start-End Cursors
        if durationFlag == 2:
            self.axes.axvline(tStart,color='Navy', alpha=0.5)
            self.axes.axvline(tEnd,color='Navy', alpha=0.5)
            selected = True
        elif durationFlag == 1:
            self.axes.axvline(tStart,color='Navy', alpha=0.5)
            if playerStarted == True:
                self.axes.axvline(tEnd,color='Navy', alpha=0.5)
        else:
            if playerStarted == True:
                self.axes.axvline(tStart,color='Navy', alpha=0.5)
                self.axes.axvline(tEnd,color='Navy', alpha=0.5)
        if playFlag == False:
            self.axes.plot(self.timeArrayToPlot[iS:iE],self.signalToPlot[iS:iE],color=c, alpha=0.65)
        elif playFlag == True:
            self.axes.plot(self.timeArrayToPlot[iS:iE],self.signalToPlot[iS:iE],color='black')

        # >> Zero Clicks , Counters and Flags -> Release Button Function
        #----------------------
        if counterClick >= 3:
            xStart = 0
            xEnd = 0
            tempPass = False
            playerStarted = False
            tempPass = False
            counterClick = 1
            annotationFlag = False
            isDeleted = False
            isBold = False

    # >> BOLD SELECTED SEGMENT
    #----------------------
    def drawBold(self, c):
        global xPos, yPos, isBold, annotations
        global startTimeToPlay, endTimeToPlay, counterClick
        global overlap
        global text1, text2
        global selected, isAbove

        tStart = float(startTimeToPlay)/1000.0
        tEnd = float(endTimeToPlay)/1000.0
        iS = np.argmin(np.abs(self.timeArrayToPlot - tStart))
        iE = np.argmin(np.abs(self.timeArrayToPlot - tEnd))

        start = tStart * 1000
        end = tEnd *1000
        text1 = ' '
        text2 = ' '
        text = ' '

        #position to diplay Class-Text
        positionPlotText = (tStart+tEnd)/2

        #check for change existing annotation
        #----------------------
        for class1 in range(len(annotations)):
            if start == annotations[class1][0] and end == annotations[class1][1]:
                text1 = annotations[class1][2]
                for class2 in range(len(annotations)):
                    if (annotations[class1][0] < annotations[class2][0] and annotations[class1][1] > annotations[class2][1] or
                        annotations[class1][0] > annotations[class2][0] and annotations[class1][1] < annotations[class2][1] or
                        annotations[class1][0] < annotations[class2][0] and annotations[class1][1] > annotations[class2][0] or
                        annotations[class1][0] < annotations[class2][1] and annotations[class1][1] > annotations[class2][1]):
                        text2 = annotations[class2][2]

        #find if segment is above or not
        for class1 in range(len(annotations)):
            if start == annotations[class1][0] and end == annotations[class1][1]:
                text1 = annotations[class1][2]
                for class2 in range(len(annotations)):
                        if annotations[class1][0] < annotations[class2][0] and annotations[class1][1] > annotations[class2][1]:
                            isAbove = True
        if text2 != ' ':
            text = text1 + ' & ' + text2
            overlap = True
        else:
            text = text1
            overlap = False

        # >> Plot Class-Text and Bold Line
        self.axes.text(positionPlotText, 3100, text,horizontalalignment='center',verticalalignment='center')
        self.axes.plot(self.timeArrayToPlot[iS:iE],self.signalToPlot[iS:iE],color=c, linewidth=3.5) 

        #flag isBold -> test on clear if selected area is bold to return in normal plot
        isBold = True
        selected = False


    def annotationMenu(self):
        global annotations, classLabels
        global startTimeToPlay, endTimeToPlay, overlap, isAbove
        global text1, text2

        speakers = []
        passAppend = True

        annotation = QMenu()

        for index in range(len(annotations)):
            if startTimeToPlay==annotations[index][0] and endTimeToPlay==annotations[index][1]:
                if not overlap:
                    delete = annotation.addAction('Delete')
                    delete.triggered.connect(self.delete)
                elif overlap and isAbove:
                    delete = annotation.addMenu('Delete')
                    delete.addAction(text1)
                    delete.addAction(text2)
                    delete.triggered.connect(self.deleteFromOverlap)
                    isAbove = False
                elif overlap:
                    delete = annotation.addAction('Delete')
                    delete.triggered.connect(self.delete)
                    overlap = False
        self.subMenu = annotation.addMenu('Annotate')
        
        #Define Labels
        #----------------------
        for i in range(len(classLabels)):
            self.subMenu.addAction(classLabels[i])

        #Define Speakers
        #----------------------
        speakerMenu = self.subMenu.addMenu('Speech')
        for i in range(len(annotations)):
            if annotations[i][2][:8] == 'Speech::':
                remove = annotations[i][2].index(':')
                remove = remove + 2
                length = len(annotations[i][2])
                sub = length - remove
                if not annotations[i][2][-sub:] in speakers:
                    speakers.append(annotations[i][2][-sub:])
                #speakerMenu.addAction(speaker)
        #new speaker...
        for index in range(len(speakers)):
            speakerMenu.addAction(speakers[index])
        addNew = speakerMenu.addAction('Add New Speaker')

        self.subMenu.triggered.connect(self.chooseAnnotation)
        speakerMenu.triggered.connect(self.Speakers)

        annotation.exec_(self.mapToGlobal(self.pos()) + QtCore.QPoint(xPos, yPos))

    # >> Delete annotated segment in overlaping case
    def deleteFromOverlap(self, action):
        global isDeleted, counterClick, isBold, chartFig, shadesAndSpeaker
        global xCheck
        global text1, text2
        start, end = 0, 0
        label =  action.text()
        segDuration = []

        #Find overlap segment duration
        for element in range(len(annotations)):
            if xCheck>=annotations[element][0] and xCheck<=annotations[element][1]:
                segDuration.append([annotations[element][0], annotations[element][1]])  

        #max startTime and max endTime
        for i in range(len(segDuration)):
            if start < segDuration[i][0]:
                start = segDuration[i][0]
        for j in range(len(segDuration)):
            if end < segDuration[j][1]:
                end = segDuration[j][1]

        for element in range(len(annotations)):
            #check for deletion
            if label == annotations[element][2] and start<=annotations[element][0] and end>=annotations[element][1]:
                annotations.remove(annotations[element])
                break
        #Re-Write annotations in csv file with changes
        csvFileName = bagFile.replace(".bag","_audio.csv")
        self.annotationFile = open(csvFileName, 'w')
        write = csv.writer(self.annotationFile)
        write.writerows(annotations)
        self.annotationFile.close()
        isDeleted = True
        isBold = False
        counterClick = counterClick - 1
        self.clear()

        #if csv is empty -> delete file
        if not annotations:
            os.remove(csvFileName)

        chartFig.axes.clear()
        chartFig.drawChart()
        chartFig.draw()


    # >> Delete Annotated Segments
    #----------------------
    def delete(self):
        global isDeleted, counterClick, isBold, chartFig, shadesAndSpeaker
        tempDelete = None
        # >> Find element to delete
        for element in range(len(annotations)):
            #check for deletion
            if startTimeToPlay == annotations[element][0] and endTimeToPlay == annotations[element][1]:
                tempDelete = annotations[element][2]
                annotations.remove(annotations[element])
                break
        
        #Re-Write annotations in csv file with changes
        #----------------------
        csvFileName = bagFile.replace(".bag","_audio.csv")
        self.annotationFile = open(csvFileName, 'w')
        write = csv.writer(self.annotationFile)
        write.writerows(annotations)
        self.annotationFile.close()
        isDeleted = True
        isBold = False
        counterClick = counterClick - 1
        self.clear()

        #if csv is empty -> delete file
        if not annotations:
            os.remove(csvFileName)

        chartFig.axes.clear()
        chartFig.drawChart()
        chartFig.draw()

    # >> Annotate Speakers
    #----------------------
    def Speakers(self, action):
        global text_, colorName, chartFig

        text = action.text()

        if text == 'Add New Speaker':
            self.newSpeaker()
        else:
            text_ = 'Speech::' + text
            self.saveAnnotation()
            self.draw()
            chartFig.axes.clear()
            chartFig.drawChart()
            chartFig.draw()

    # >> Add new speaker
    #----------------------
    def newSpeaker(self):
        self.new = MyPopup()
        self.new.setGeometry(QRect(500, 100, 300, 100))
        self.new.show()

    # >> Annotate Audio Segments from Annotation Menu
    #----------------------
    def chooseAnnotation(self, action):
        global colorName
        global text_, greenIndex, GreenShades
        global chartFig, doIt

        doIt = False

        text = action.text()
        text_ = text


        if text == 'Speech':
            colorName = 'green'
            doIt = True

        elif text == 'Music':
            colorName = 'red'
            doIt = True

        elif text == 'Activity':
            colorName = 'magenta'
            doIt = True

        elif text == 'Laugh':
            colorName = 'yellow'
            doIt = True
        elif text == 'Cough':
            colorName = '#4B0082'
            doIt = True
        
        if doIt:
            self.saveAnnotation()
            self.draw()
            chartFig.axes.clear()
            chartFig.drawChart()
            chartFig.draw()


    # >> PLOT ANNOTATIONS SAVED ON .CSV FILE
    #----------------------
    def drawAnnotations(self):
        global greenIndex, GreenShades,shadesAndSpeaker, counterClick

        color = None
        for index in range(len(annotations)):
            startAnnotation = float(annotations[index][0])/1000.0
            endAnnotation = float(annotations[index][1])/1000.0
            iStart = np.argmin(np.abs(self.timeArrayToPlot - startAnnotation))
            iEnd = np.argmin(np.abs(self.timeArrayToPlot - endAnnotation))
            # if Speech define greenshade
            if annotations[index][2][:8] == 'Speech::':
                for shadeIndex in range(len(shadesAndSpeaker)):
                    if annotations[index][2] == shadesAndSpeaker[shadeIndex][0]:
                        color = shadesAndSpeaker[shadeIndex][1]
                pass
            # annotate rest of Classes
            else:
                for colorIndex in range(len(annotationColors)):
                    if annotationColors[colorIndex][0] == annotations[index][2]:
                        color = annotationColors[colorIndex][1]
            self.axes.plot(self.timeArrayToPlot[iStart:iEnd],self.signalToPlot[iStart:iEnd],color=color)

                                       
    # >> Save current ANNOTATION
    #----------------------
    def saveAnnotation(self):
        global annotationFlag, annotations, shadesAndSpeaker, counterClick
        global startTimeToPlay, endTimeToPlay, colorName, isDeleted, isBold
        global greenIndex, GreenShades, shadesAndSpeaker, text_

        annotationChange = False
        speakerExist = False

        # >> Define start-end annotation time
        startAnnotation = float(startTimeToPlay)/1000.0
        endAnnotation = float(endTimeToPlay)/1000.0
        iStart = np.argmin(np.abs(self.timeArrayToPlot - startAnnotation))
        iEnd = np.argmin(np.abs(self.timeArrayToPlot - endAnnotation))

        checkStart = startAnnotation * 1000
        checkEnd = endAnnotation * 1000

        # >> Check for change existing annotation
        for index in range(len(annotations)):
            if checkStart == annotations[index][0] and checkEnd == annotations[index][1]:
                annotations[index][2] = text_
                for i in range(len(shadesAndSpeaker)):
                    if text_ == shadesAndSpeaker[i][0]:
                        colorName = shadesAndSpeaker[i][1]
                        speakerExist = True
                        break

        # >> Merge Annotations (side by side)
        for index in range(len(annotations)):
            if checkEnd == annotations[index][0] and text_ == annotations[index][2]: 
                annotations[index][0] = startTimeToPlay
                annotations.remove(annotations[index-1])
                annotationChange = True
                break
            if checkStart == annotations[index][1] and text_ == annotations[index][2]:
                annotations[index][1] = endTimeToPlay
                annotations.remove(annotations[index+1])
                annotationChange = True
                break
            if checkStart <= annotations[index][0] and checkEnd >= annotations[index][1] and text_ == annotations[index][2]:
                annotations[index][0] = startTimeToPlay
                annotations[index][1] = endTimeToPlay
                print checkStart, checkEnd
                annotationChange = True
                break

        if not annotationChange:    
            # >> List of annotations
            annotations.append([startTimeToPlay, endTimeToPlay, text_])
            for i in range(len(shadesAndSpeaker)):
                if text_ == shadesAndSpeaker[i][0]:
                    colorName = shadesAndSpeaker[i][1]
                    speakerExist = True
                    break
                else:
                    colorName = GreenShades[greenIndex]

        if not speakerExist:
            if greenIndex >= len(GreenShades):
                greenIndex = 0
            else:
                greenIndex = greenIndex + 1
            shadesAndSpeaker.append([text_, colorName])

            annotationChange = False
        
        
        # >> Write annotations in csv file
        csvFileName = bagFile.replace(".bag","_audio.csv")
        self.annotationFile = open(csvFileName, 'w')
        write = csv.writer(self.annotationFile)
        write.writerows(annotations)
        self.annotationFile.close()

        # >> Plot Annotated Segment 
        annotationFlag = True
        isBold = False
        counterClick = counterClick - 1
        self.clear()
        chartFig.axes.clear()
        chartFig.drawChart()
        chartFig.draw()
    
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  GUI FUNCTION                                                                           #
#  called from run Functions                                                              #
#  Initilize Graphical Interface widgets                                                  #
#  Enable QtMultimedia Player                                                             #
#  Enable annotation and gantt chart plots                                                #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class ApplicationWindow(QtWidgets.QMainWindow):
    global wavFileName
    global fig,chartFig
    global duration, counterClick
    global colorName, text_
    global startAnnotation, endTimeToPlay

    # >> QtMultimedia Signals
    #----------------------
    play = pyqtSignal()
    pause = pyqtSignal()
    stop = pyqtSignal()

    def __init__(self):
        global playerStarted
        global wavFileName, fig, chartFig
        global playerStarted, durationFlag, duration
        global colorName, text_, counterClick
        global startAnnotation, endTimeToPlay

        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.main_widget = QtWidgets.QWidget(self)
        playerStarted = False

        #DEFINE PLAYER-PLAYLIST   
        #----------------------
        self.source = QtCore.QUrl.fromLocalFile(os.path.abspath(wavFileName))
        self.content = QMediaContent(self.source)
        self.player = QMediaPlayer()
        self.playlist = QMediaPlaylist(self)
        self.playlist.addMedia(self.content)
        self.player.setPlaylist(self.playlist)

        # >> Define annotations and gantt chart 
        #---------------------- 
        self.wave = Waveform()
        fig = self.wave
        self.chart = Chart()
        chartFig = self.chart

        # >> Define player buttons 
        #---------------------- 
        playButton = QPushButton("Play")
        pauseButton = QPushButton("Pause")
        stopButton = QPushButton("Stop")

        # >> Define layouts 
        #---------------------- 
        waveLayout = QVBoxLayout()
        waveLayout.addWidget(self.wave)
        waveLayout.addWidget(self.chart)

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
        waveLayout.addWidget(line)

        #Buttons layout
        buttonLayout = QVBoxLayout()
        buttonLayout.addWidget(playButton)
        buttonLayout.addWidget(pauseButton)
        buttonLayout.addWidget(stopButton)
        buttonLayout.setAlignment(Qt.AlignTop)


        # >> Specify final layout align 
        #----------------------
        layout = QHBoxLayout(self.main_widget)
        layout.addLayout(waveLayout)
        layout.addLayout(buttonLayout)
        
        # >> Define buttons connections 
        #---------------------- 
        playButton.clicked.connect(self.Play)
        pauseButton.clicked.connect(self.Pause)
        stopButton.clicked.connect(self.Stop)


        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)


    # PLAYER BUTTON FUNCTIONS

    # >> Play audio (whole signal or segment) 
    #---------------------- 
    def Play(self):
        global playerStarted
        global durationFlag
        global duration, counterClick
        global startTimeToPlay, endTimeToPlay, first

        #GET CLICKS FROM WAVEFORM
        #---------------------- 
        #Initialize connection-position ONCE
        if not playerStarted:
            #10ms for changePosition -> Not Delaying
            self.player.positionChanged.connect(self.checkPositionToStop)
            self.player.setNotifyInterval(10)
            if durationFlag==0:
                playerStarted = True
                startTimeToPlay = 0
                self.start = startTimeToPlay
                self.end = duration*1000 - 10
                endTimeToPlay = self.end
                counterClick = 3
            elif durationFlag==1:
                playerStarted = True
                self.start = startTimeToPlay
                self.end = duration*1000 - 10
                endTimeToPlay = self.end
                counterClick = 3
            elif durationFlag==2:
                playerStarted = True
                self.start = startTimeToPlay
                self.end = endTimeToPlay
            self.player.setPosition(self.start)

        playFlag = True
        self.player.play()

    # >> Pause audio playing 
    #----------------------
    def Pause(self):
        #Not begging from self.start
        playerStarted = True
        self.player.setPosition(self.time_)
        self.player.pause()

    # >> Stop audio playing 
    #----------------------
    def Stop(self):
        self.player.stop()
        #Begin again segment
        self.start = startTimeToPlay
        self.player.setPosition(self.start)

    # >> Check ms in audio to stop play 
    #----------------------
    def checkPositionToStop(self):
        self.time_ = self.player.position()
        print self.time_
        if self.time_ >= self.end:
            self.Stop()
            self.player.setPosition(self.start)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  MAIN FUNCTION                                                                          #
#  called from rosbag_audio.py                                                            #
#  run ApplicationWindow to intialize Graphical Interface                                 #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


def run(wavFileName2,bagFile2):
    global wavFileName
    global bagFile
    global xStart
    global xEnd
    global annotationFlag, annotations, shadesAndSpeaker, greenIndex
    global spf, duration, signal

    time = 0
    segmentDuration = 0
    segments = []

    # >> Open WAVfile 
    #----------------------
    #wavFileName -> global variable 
    wavFileName = wavFileName2
    bagFile = bagFile2

    spf = wave.open(wavFileName,'r')
    #Extract Raw Audio from Wav File
    signal = spf.readframes(-1)
    signal = np.fromstring(signal, 'Int16')
    #self.axes.clear()

    #Get wavFile duration
    frames = spf.getnframes()
    rate = spf.getframerate()
    duration = frames / float(rate)

    # >> Open CSVfile 
    #----------------------
    # check if .csv exists
    csvFileName = bagFile.replace(".bag","_audio.csv")
    if os.path.isfile(csvFileName):
        # print '.csv Found !'
        annotationFile = open(csvFileName, 'rb')

        read = csv.reader(annotationFile)
        for row in read:
            row[0] = float(row[0])
            row[1] = float(row[1])
            annotations.append([row[0], row[1], row[2]])

        # get speakers unic colors for annotation plot and ganttChart
        for shadeIndex in range(len(annotations)):
            if annotations[shadeIndex][2][:8] == 'Speech::':
                shadesAndSpeaker.append([annotations[shadeIndex][2], GreenShades[greenIndex]])
                if greenIndex > len(GreenShades):
                    greenIndex = 0
                else:
                    greenIndex = greenIndex + 1

    # >> Call Classifier in case CSVFile not exists 
    #---------------------- 
    else:
        # print 'classifier...'
        [flagsInd, classesAll, acc] = aS.mtFileClassification(wavFileName, 'svmModelTest', 'svm', False)
        # declare classes
        [segs, classes] = aS.flags2segs(flagsInd, 1)
        lengthClass = len(classesAll)
        className = np.arange(lengthClass, dtype=np.float)


        for j in range(len(segs)):
            # no Annotation for Silence segments
            for i in range(len(classesAll)):
                if classes[j] == className[i] and classesAll[i] != 'Silence':
                    annotations.append([segs[j][0]*1000, segs[j][1]*1000, classesAll[i]])




    # >> Initialize GUI 
    #----------------------
    qApp = QtWidgets.QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.setWindowTitle("Audio")
    aw.show()

    # >> Terminate GUI 
    #---------------------- 
    sys.exit(qApp.exec_())