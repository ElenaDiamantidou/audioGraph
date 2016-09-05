import os
import sys
from pyAudioAnalysis import audioFeatureExtraction as aF
from pyAudioAnalysis import audioTrainTest as aT
from pyAudioAnalysis import audioBasicIO


if __name__ =='__main__':

    #classify
    Result, P, classNames = aT.fileClassification('Speech/Speech_2.wav', 'svmModelTest','svm')
    print Result
    print P
    print classNames