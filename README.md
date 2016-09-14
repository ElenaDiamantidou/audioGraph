# audioGraph

DEPENDENCIES
------------
**OS** : Ubuntu 16.04 edition

**Python 2.7.0**

**Ros Kinetic** 
http://wiki.ros.org/kinetic/Installation/Ubuntu

**NUMPY**

*sudo apt-get install python-numpy*

**MATPLOTLIB**

*sudo apt-get install python-matplotlib*

**ffmpeg**

*sudo add-apt-repository ppa:mc3man/trusty-media*

*sudo apt-get update*

*sudo apt-get dist-upgrade*

*sudo apt-get install ffmpeg*

**PyQT5**

install PyQt5 from Synaptics

*always run sudo synaptics

**if gstreamer not automatically installed, install also from synaptics

**QtMultimedia**

install QtMultimedia from Synaptics

**check Roslib**

*dpkg -L python-roslib*

dpkg-query: package 'python-roslib' is not installed

Use dpkg --info (= dpkg-deb --info) to examine archive files,

and dpkg --contents (= dpkg-deb --contents) to list their contents.

If python-roslib is not installed: 

*sudo apt-get install python-roslib*
 
**pyAudioAnalysis**

install library from https://github.com/tyiannak/pyAudioAnalysis

the latest edition needs to install sklearn and hmmlearn

*sudo apt-get install python-pip*

*sudo pip install -U sklearn*

*sudo pip install hmmlearn*

HOW TO RUN TOOL
---------------
*python rosbagAudio.py rosbags/2016-07-04-16-19-14.bag*

where 2016-07-04-16-19-14.bag the rosbag file.

To split audio into segments run:

*python saveAudioSegments.py rosbags/2016-07-22-13-24-10_audio.csv rosbags/2016-07-22-13-24-10.wav*

To train pyAudioAnalysis Classifier run:

*python trainAudioFromAnnotations.py*

:smiley:
