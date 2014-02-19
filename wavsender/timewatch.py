# coding: utf-8
from datetime import datetime



class TWClass(object):
    def __init__(self):
        self.time_watch_mass = {}
        self.time_watch_first_start = False

    def time_watch(self, func):
        start = datetime.now()
        if not self.time_watch_first_start:
            self.time_watch_first_start = start
        ret = func()
        end = datetime.now()
        #print "func", 
        if func.__name__ in self.time_watch_mass:
            self.time_watch_mass[func.__name__].append(end-start)
        else:
            self.time_watch_mass[func.__name__] = [end-start,]
        return ret
    
    def print_time_watch(self):
        print "_____first start______"
        for a in self.time_watch_mass:
            print "func", a, "time:", self.time_watch_mass[a][0]
        print "_____sums______[work time:", datetime.now()-self.time_watch_first_start, "]"
        for a in self.time_watch_mass:
            sm = self.time_watch_mass[a][0]
            for n in self.time_watch_mass[a][1:]:
                sm += n
            print "func", a, "sum time:", sm
            
TW = TWClass()