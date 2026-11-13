"""Detecção local de documento, estabilidade e correção de perspectiva."""
import cv2
import numpy as np

def detect_document(frame):
    h,w=frame.shape[:2];scale=min(1,800/max(h,w));small=cv2.resize(frame,None,fx=scale,fy=scale)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(cv2.GaussianBlur(gray,(5,5),0),50,150)
    edges=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    contours,_=cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours,key=cv2.contourArea,reverse=True)[:12]:
        poly=cv2.approxPolyDP(contour,.025*cv2.arcLength(contour,True),True)
        if len(poly)==4 and cv2.isContourConvex(poly) and cv2.contourArea(poly)>small.shape[0]*small.shape[1]*.18:
            p=poly.reshape(4,2).astype('float32')/scale
            if min(p[:,0])<3 or min(p[:,1])<3 or max(p[:,0])>w-4 or max(p[:,1])>h-4:continue
            center=p.mean(axis=0);p=p[np.argsort(np.arctan2(p[:,1]-center[1],p[:,0]-center[0]))]
            p=np.roll(p,-np.argmin(p.sum(axis=1)),axis=0)
            return p
    return None

def rectify(frame,points):
    if points is None:return frame.copy()
    a,b,c,d=points
    w=int(max(np.linalg.norm(a-b),np.linalg.norm(c-d)));h=int(max(np.linalg.norm(a-d),np.linalg.norm(b-c)))
    if min(w,h)<50:raise ValueError('Aproxime o documento da câmera.')
    matrix=cv2.getPerspectiveTransform(points.astype('float32'),np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],np.float32))
    return cv2.warpPerspective(frame,matrix,(w,h))

class StableCapture:
    def __init__(self):self.previous=None;self.since=None;self.locked=False
    def update(self,points,now):
        if points is None:
            self.previous=None;self.since=None;self.locked=False;return False
        if self.locked:return False
        if self.previous is None or np.max(np.linalg.norm(points-self.previous,axis=1))>12:self.since=now
        self.previous=points.copy()
        if self.since is not None and now-self.since>=1.2:
            self.locked=True;return True
        return False
