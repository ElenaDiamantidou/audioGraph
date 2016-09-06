#!/usr/bin/env python
import roslib
import cv2
#audio packages
#import audio_common_msgs
#from cv_bridge import CvBridge, CvBridgeError
#import rospy
from std_msgs.msg import String
import signal
import os
import sys
import time
import threading
import rosbag
import yaml
import numpy as np
import argparse
import textwrap
import struct
import wave
import subprocess
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
import gui

programmName = os.path.basename(sys.argv[0])

#input parameters
def parse_arguments():
    inputFile = sys.argv[-1]
    #print inputFile 
    return inputFile
    

#isolate audio from bag file
def audio_bag_file(bagFile):
    #save topic and message

    topicKey = 0
    topic = 0
    flag = False
    bag = rosbag.Bag(bagFile)
    info_dict = yaml.load(bag._get_yaml_info())
    topics =  info_dict['topics']

    for key in range(len(topics)):
        if topics[key]['topic'] == '/audio':
            topicKey = key

    topic = topics[topicKey]
    messages =  topic['messages']
    duration = info_dict['duration']
    topic_type = topic['type']
    frequency = topic['frequency']

    audioCheck = topic['topic']
    #Checking if the topic is audio
    if 'audio_common_msgs' in topic_type:
        sound = True
        print "Audio found"
    else:
        sound = False
        print "Such a pity..."

    audio = []
    if sound == True:
        for topic, msg, t in bag.read_messages(topics=['/audio']):
            audio += msg.data
    nBytes = len(audio)
    nSamples = nBytes / 2    
    print "total number of compressed bytes {0:d}".format(nBytes)
    print "total number of compressed bytes {0:d}".format(nSamples)
    print "total duration {0:.2f}".format(duration)
    print "average bit rate {0:.2f}".format(float(nBytes) * 8.0 / float(duration))

    frequency = frequency * 1000
    #bag.close()    
    return audio

#save mp3 file
def write_mp3_file(audioData, bagFile):
    mp3FileName = bagFile.replace(".bag",".mp3")
    mp3_file = open(mp3FileName, 'w')
    mp3_file.write(''.join(audioData))
    mp3_file.close()
    return mp3FileName

#convert mp3 to wav
def mp3_to_wav(mp3Path):
    #call arg not file...
    wavFileName = mp3Path.replace(".mp3",".wav")
    subprocess.call(['ffmpeg', '-i', mp3Path,'-y', '-ar', '16000', '-ac', '1', wavFileName])
    return wavFileName

#play wav file
def play_wav(wavFileName):
    #-nodisp   : display not in new window
    #-autoexit : stop automatically
    #-ss       : start time
    #-t        : duration
    subprocess.call(['ffplay', '-nodisp', '-autoexit','-ss','0', '-t', '3.5', wavFileName])


#Plot waveform in GUI
#create waveform of wav file
def createWaveform(wavFileName):
    spf = wave.open(wavFileName,'r')
    #Extract Raw Audio from Wav File
    signal = spf.readframes(-1)
    signal = np.fromstring(signal, 'Int16')

    #If Stereo
    if spf.getnchannels() == 2:
        print 'Just mono files'
        sys.exit(0)

    fig = plt.figure(1)
    plt.title('Signal Wave...')
    plt.plot(signal)
    play_wav(wavFileName)
    
    plt.grid()
    plt.show()


#main
if __name__ =='__main__':
    #read bag file
    bagFile = parse_arguments()
    audioData = audio_bag_file(bagFile) 
    # get audio data 
    mp3FileName = write_mp3_file(audioData, bagFile)
    wavFileName = mp3_to_wav(mp3FileName)
    gui.run(wavFileName, bagFile)


    


