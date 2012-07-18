#   Copyright 2012 Oli Schacher
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# $Id: threadpool.py 7 2009-04-09 06:51:25Z oli $
#
import threading
import time
import Queue
import logging

class ThreadPool(threading.Thread):
    
    def __init__(self,minthreads=1,maxthreads=20,queuesize=100):
        self.workers=[]
        self.queuesize=queuesize
        self.tasks=Queue.Queue(queuesize)
        self.minthreads=minthreads
        self.maxthreads=maxthreads
        assert self.minthreads>0
        assert self.maxthreads>self.minthreads
        
        self.logger=logging.getLogger('postomaat.threadpool')
        self.threadlistlock=threading.Lock()
        self.checkinterval=10
        self.threadcounter=0
        self.stayalive=True
        self.laststats=0
        self.statinverval=60
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.start()
        
        
        
        
        
    
    def add_task(self,session):
        self.tasks.put(session)
    
    def get_task(self):
        try:
            session=self.tasks.get(True, 5)
            return session
        except Queue.Empty:
            return None
        
         
    
    def run(self):
        self.logger.debug('Threadpool initialising. minthreads=%s maxthreads=%s maxqueue=%s checkinterval=%s'%(self.minthreads,self.maxthreads,self.queuesize,self.checkinterval) )
        
        
        while self.stayalive:
            curthreads=self.workers
            numthreads=len(curthreads)
            
            #check the minimum boundary
            requiredminthreads=self.minthreads
            if numthreads<requiredminthreads:
                diff=requiredminthreads-numthreads
                self._add_worker(diff)
                continue
            
            #check the maximum boundary
            if numthreads>self.maxthreads:
                diff=numthreads-self.maxthreads
                self._remove_worker(diff)
                continue
            
            changed=False
            #ok, we are within the boundaries, now check if we can dynamically adapt something
            queuesize=self.tasks.qsize()
            
            #if there are more tasks than current number of threads, we try to increase
            workload=float(queuesize)/float(numthreads)
            
            if workload>1 and numthreads<self.maxthreads:
                self._add_worker()
                numthreads+=1
                changed=True
                
            
            if workload<1 and numthreads>self.minthreads:
                self._remove_worker()
                numthreads-=1
                changed=True
            
            #log current stats
            if changed or time.time()-self.laststats>self.statinverval:
                workerlist=",".join(map(repr,self.workers))
                self.logger.debug('queuesize=%s workload=%.2f workers=%s workerlist=%s'%(queuesize,workload,numthreads,workerlist))
                self.laststats=time.time()
                
            time.sleep(self.checkinterval)
        for worker in self.workers:
            worker.stayalive=False
        del self.workers
        self.logger.info('Threadpool shut down')
    
    
    def _remove_worker(self,num=1):
        self.logger.debug('Removing %s workerthread(s)'%num)
        for bla in range(0,num):
            worker=self.workers[0]
            worker.stayalive=False
            del self.workers[0]
        
    
    def _add_worker(self,num=1):
        self.logger.debug('Adding %s workerthread(s)'%num)
        for bla in range(0,num):
            self.threadcounter+=1
            worker=Worker("[%s]"%self.threadcounter,self)
            self.workers.append(worker)
            worker.start()
    

class Worker(threading.Thread):
    def __init__(self,workerid,pool):
        threading.Thread.__init__(self)
        self.workerid=workerid
        self.birth=time.time()
        self.pool=pool
        self.stayalive=True
        self.logger=logging.getLogger('postomaat.threads.worker.%s'%workerid)
        self.logger.debug('thread init')
        self.noisy=False
        self.setDaemon(False)
    
    def __repr__(self):
        return self.workerid    
       
    def run(self):
        self.logger.debug('thread start')
        while self.stayalive:
            time.sleep(0.1)
            
            if self.noisy:
                self.logger.debug('Getting new task...')
            sesshandler=self.pool.get_task()
            if sesshandler==None:
                if self.noisy:
                    self.logger.debug('Queue empty')
                continue
            
            if self.noisy:
                self.logger.debug('Doing work')
            try:
                sesshandler.handlesession()
            except Exception,e:
                self.logger.error('Unhandled Exception : %s'%e)
        
        
        self.logger.debug('thread end')

    
      