from urllib import request
import random
from multiprocessing.dummy import Pool
import os
import tarfile
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
import io
import threading
import sys
import traceback
import requests

tempDirName = "temp"
targetXResolution = 256
targetYResolution = 256
useImageCountPerClass = 30
saveImagePath = "G:\\images"
checkPointId = ""

class ImageData:
    def __init__(self):
        name=""
        url=""
        bb_xmin=0
        bb_xmax=0
        bb_ymin=0
        bb_ymax=0
        width=0
        height=0

def loadIdList():
    print("load bbList...")
    bbFileName = "bbIdList.txt"
    if os.path.exists(bbFileName):
        with open(bbFileName, "r") as listData:
            bbList = []
            for line in listData:
                bbList.append(line.rstrip('\n'))
            return bbList

    idListURL = "http://www.image-net.org/api/text/imagenet.bbox.obtain_synset_list"
    with request.urlopen(idListURL) as response:
        idList = response.read()
        with open(bbFileName, "w") as listData:
            outputList = idList.decode('ISO-8859-1').split()
            for line in outputList:
                listData.write(str(line) + "\n")
            print("load bb complete")
            return outputList
    
    return None

def loadBoundBox(id):
    #print("load bbFile of " + id)
    BoundBoxBaseURL = "http://image-net.org/downloads/bbox/bbox/{}.tar.gz"
    BoundBoxURL = BoundBoxBaseURL.format(id)
    os.makedirs(tempDirName+"/"+id, exist_ok=True)
    dirPath = tempDirName+"/"+id
    try:
        request.urlretrieve(BoundBoxURL, dirPath+"/"+id+".tar.gz")
    
    except KeyboardInterrupt:
        os._exit(0)
    except:
        return False
    
    else:
        unpackSpooler.append((id, dirPath))
            
        return True

def getValidImages(id):
    validImageDatas = []
    dirPath = tempDirName+"/"+id+"/Annotation/"+id
    xmlList = os.listdir(dirPath)
    tempValidImageDatas = getValidImageDatas(dirPath, xmlList)
    imageSourceBaseURL = "http://www.image-net.org/api/text/imagenet.synset.geturls.getmapping?wnid={}"
    imageSourceURL = imageSourceBaseURL.format(id)
    #with request.urlopen(imageSourceURL) as response:
    #    html = response.read()
    #data = html.decode('utf-8')
    data = requests.get(imageSourceURL).text
    dataList = data.split()
    imageNames = dataList[::2]
    imageURLs = dataList[1::2]

    for d in tempValidImageDatas:
        try:
            index = imageNames.index(d.name)
            d.url = imageURLs[index]
            validImageDatas.append(d)
        except:
            pass
        
    return validImageDatas
        


def getValidImageDatas(dirPath, xmlList):
    tempList = []
    print("xml Process Start")
    for temp in xmlList:
        
        tree = ET.parse(dirPath+"/"+temp)
        tempData = ImageData()
        tempData.name = tree.find("filename").text
        bb_xmin = int(tree.find("object/bndbox/xmin").text)
        bb_xmax = int(tree.find("object/bndbox/xmax").text)
        bb_ymin = int(tree.find("object/bndbox/ymin").text)
        bb_ymax = int(tree.find("object/bndbox/ymax").text)
        tempData.bb_xmin = bb_xmin
        tempData.bb_xmax = bb_xmax
        tempData.bb_ymin = bb_ymin
        tempData.bb_ymax = bb_ymax
        width = int(tree.find("size/width").text)
        height = int(tree.find("size/height").text)
        tempData.width = width
        tempData.height = height

        if(tempData in tempList):
            continue
        
        if (width < targetXResolution or height < targetYResolution):
            continue
        
        if(bb_xmax - bb_xmin >= targetXResolution or bb_ymax - bb_ymin >= targetYResolution):
            continue
        
        
        tempList.append(tempData)
    print("xml process finish")
    return tempList

def trimming(image, imageData):
    leftUpX = 0
    leftUpY = 0
    Xgap = targetXResolution - (imageData.bb_xmax - imageData.bb_xmin)
    Ygap = targetYResolution - (imageData.bb_ymax - imageData.bb_ymin)
    leftUpX = imageData.bb_xmin - Xgap / 2
    leftUpY = imageData.bb_ymin - Ygap / 2

    if imageData.bb_xmin < (Xgap / 2):
        leftUpX = 0
    
    if imageData.bb_ymin < (Ygap / 2):
        leftUpY = 0
    
    if leftUpX + targetXResolution > imageData.width:
        leftUpX -= (leftUpX + targetXResolution - imageData.width)
    
    if leftUpY + targetYResolution > imageData.height:
        leftUpY -= (leftUpY + targetYResolution - imageData.height)
    
    trimmed = image.crop((leftUpX, leftUpY, leftUpX + targetXResolution, leftUpY + targetYResolution))
    return trimmed

isUnpackFinish = False
isCheckBBFinish = False            
isDownloadFinish = False
isTrimFinish = False
isSaveFinish = False
#id, dir
unpackSpooler = []
def UnpackBBData():
    while True:
        try:
            if len(unpackSpooler) == 0:
                if isUnpackFinish:
                    print("unpack finish")
                    global isCheckBBFinish
                    isCheckBBFinish = True
                    return
                continue
            else:
                with tarfile.open(unpackSpooler[0][1] + "/" + unpackSpooler[0][0] + ".tar.gz", "r:gz") as tf:  
                    print("unpack:" + unpackSpooler[0][1])
                    def is_within_directory(directory, target):
                        
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                    
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        
                        return prefix == abs_directory
                    
                    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    
                        for member in tar.getmembers():
                            member_path = os.path.join(path, member.name)
                            if not is_within_directory(path, member_path):
                                raise Exception("Attempted Path Traversal in Tar File")
                    
                        tar.extractall(path, members, numeric_owner=numeric_owner) 
                        
                    
                    safe_extract(tf, path=unpackSpooler["0"]["1"])
                    print("finish")
                    
                print("finish unpack")
                checkBBSpooler.append(unpackSpooler[0][0])
                unpackSpooler.remove(unpackSpooler[0])
        
        except KeyboardInterrupt:
            print("KeyboardInterupt")
            os._exit(0)
        except Exception as e:
            print("unpack_error")
            print(e)

#id
checkBBSpooler = []
def CheckBB():
    while True:
        try:
            if len(checkBBSpooler) == 0:
                if isCheckBBFinish:
                    print("checkbb finish")
                    global isDownloadFinish
                    isDownloadFinish = True
                    return
                continue
            else:
                print("check:"+checkBBSpooler[0])
                validImageDatas = getValidImages(checkBBSpooler[0])
                downloadImagesSpooler.append(validImageDatas)
                print(len(downloadImagesSpooler))
                checkBBSpooler.remove(checkBBSpooler[0])
        except KeyboardInterrupt:
            print("KeyboardInterupt")
            os._exit(0)
        except Exception as e:
            print(traceback.format_exc())
            print("check_error")
            print(e)

#ImageData
downloadImagesSpooler = []
def DownloadImages():
    while True:
        try:
            if len(downloadImagesSpooler) == 0:
                if isDownloadFinish:
                    print("download finish")
                    global isTrimFinish
                    isTrimFinish = True
                    return
                continue
            else:
                i = 0
                for imageData in downloadImagesSpooler[0]:
                    try:
                        print("download:"+imageData.url)
                        bytes = io.BytesIO(request.urlopen(imageData.url, timeout=30).read())
                        im = Image.open(bytes)
                        trimImagesSpooler.append((im, imageData))
                        i+=1
                    except Exception as e:
                        print(e)

                    if i >= useImageCountPerClass:
                        break
                downloadImagesSpooler.remove(downloadImagesSpooler[0])
        except KeyboardInterrupt:
            print("KeyboardInterupt")
            os._exit(0)
        except Exception as e:
            print("download_error")
            print(e)

#image(row) ImageData
trimImagesSpooler = []
def TrimImages():
    while True:
        try:
            if len(trimImagesSpooler) == 0:
                if isTrimFinish:
                    print("trimming finish")
                    global isSaveFinish
                    isSaveFinish = True
                    return
                continue
            else:
                print("trim:"+trimImagesSpooler[0][1].name)
                trimmed = trimming(trimImagesSpooler[0][0], trimImagesSpooler[0][1])
                saveImagesSpooler.append((trimmed, trimImagesSpooler[0][1]))
                trimImagesSpooler.remove(trimImagesSpooler[0])
        except KeyboardInterrupt:
            print("KeyboardInterupt")
            os._exit(0)
        except Exception as e:
            print("trimImage_error")
            print(e)

#image(trimmed) ImageData
saveImagesSpooler = []
def SaveImages():
    while True:
        try:
            if len(saveImagesSpooler) == 0:
                if isSaveFinish:
                    print("save finish")
                    return
                continue
            else:
                print("save:"+saveImagesSpooler[0][1].name)
                img = saveImagesSpooler[0][0].convert("RGB")
                img.save(saveImagePath+"/"+saveImagesSpooler[0][1].name+".jpg", quality = 50)
                saveImagesSpooler.remove(saveImagesSpooler[0])
        except KeyboardInterrupt:
            print("KeyboardInterupt")
            os._exit(0)
        except Exception as e:
            print("save_error")
            print(e)

if __name__ == "__main__":
    idList = loadIdList()
    unpackThread = threading.Thread(target=UnpackBBData)
    unpackThread.start()

    checkBBThread = threading.Thread(target=CheckBB)
    checkBBThread.start()

    downloadImagesThread = threading.Thread(target=DownloadImages)
    downloadImagesThread.start()

    trimImagesThread = threading.Thread(target=TrimImages)
    trimImagesThread.start()

    saveImagesThread = threading.Thread(target=SaveImages)
    saveImagesThread.start()

    isCheckPointExist = False
    if checkPointId != "":
        print("check point loaded:"+checkPointId)
        isCheckPointExist = True

    for id in idList:
        if id == checkPointId:
            print("check point found")
            isCheckPointExist = False

        if isCheckPointExist:
            print("pass:"+id+":"+checkPointId)
            continue
        try:
            if not loadBoundBox(id) :
                continue
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            os._exit(0)
    
    print("Main Loop Finish")
    isUnpackFinish = True
    unpackThread.join()
    checkBBThread.join()
    downloadImagesThread.join()
    trimImagesThread.join()
    saveImagesThread.join()