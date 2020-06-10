from __future__ import division
import logging
import time
import math
from statistics import mean
import os
import configparser
import csv
import codecs
from threading import Lock, Thread

def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

class flavor:
    def __init__(self, id):
        self.lock = Lock()
        self.id = id
        self.available_host = 0  # k
        self.number_host = 0  # n
        self.requests_num = 0

    def update_counters(self, available_host, number_host):
        with self.lock:
            self.available_host += available_host
            self.number_host += number_host
            self.requests_num += 1

    def get_counters(self):
        with self.lock:
            temp = [self.available_host, self.number_host]
            self.available_host = 0
            self.number_host = 0
        return temp

    def reset_counters(self):
        self.available_host = 0  # k
        self.number_host = 0  # n
        self.requests_num = 0


class apsr_controller:

    def __init__(self):
        self.d = 3
        self.s = 1
        self.flavor_dict = {}
        self.counter = 0
        LOG_FILENAME = 'APSR_CONTROLLER.log'
        self.LOG = setup_logger(LOG_FILENAME, LOG_FILENAME)
        self.shard_flavor_info = "/lib/python2.7/site-packages/nova/scheduler/shard_flavor_info.csv"
        self.shard_d = "/lib/python2.7/site-packages/nova/scheduler/shard_d.csv"
        self.shard_s = "/lib/python2.7/site-packages/nova/scheduler/shard_s.csv"

    def update_dict_from_csv(self):
        share_flavor_file = open(self.shard_flavor_info, 'rb')  # reading CSV file
        line = share_flavor_file.readline()
	while line != "":
	    line = line.split(",")
            flavor_id = int(line[0])
            filter_host_len = int(line[1])
            try:
                flavor_obj = self.flavor_dict[flavor_id]
            except:
                new_flavor = flavor(flavor_id)
                self.flavor_dict[flavor_id] = new_flavor
                flavor_obj = self.flavor_dict[flavor_id]

            self.counter += 1

            flavor_obj.update_counters(filter_host_len , self.d)
            self.flavor_dict.update({flavor_id: flavor_obj})
            line = share_flavor_file.readline()
	
        open(self.shard_flavor_info, 'w').close()
    def choose(self, n, k):
        """
        A fast way to calculate binomial coefficients by Andrew Dalke (contrib).
        https://stackoverflow.com/questions/3025162/statistics-combinations-in-python/3027128
        """
        if 0 <= k <= n:
            ntok = 1
            ktok = 1
            for t in range(1, min(k, n - k) + 1):
                ntok *= n
                ktok *= t
                n -= 1
            return ntok // ktok
        else:
            return 0

    def prob_x_y(self, x, y):
        # by simplifie the equ - we get |X| * pi(for i=1 to Y) of i = |X| * y!
        return float(x * math.factorial(y))

    def satisfy_SLA(self, n, epsilon, k, s, b, opt_d):
        # calc E_Hs by formula (6) in article
        E_Hs = 0.0
        sigma = float(1 - (float((n - k) / n)) ** opt_d)  # eq 3
        for f in range(1, s + 1):
            comp1 = 1 - ((k - 1) / k) ** f
            comp2 = self.choose(s, f) * sigma ** f * (1 - sigma) ** (s - f)
            E_Hs += comp1 * comp2
        E_Hs = E_Hs * k
        # equlation 1 - E[Hs] - s*(1 - EPSILON) >= 0
        # equlation 2 - S * D - B <= 0
        eq1_result = E_Hs - s * (1 - epsilon)
        eq2_result = s * opt_d - b
        if eq1_result >= 0 and eq2_result <= 0:
            return True
        return False

    def max_parallizem(self, n, epsilon, b, k):
        S = 1
        while self.satisfy_SLA(n, epsilon, k, S + 1, b, math.floor(b / (S + 1))):
            S += 1
        return [S, math.floor(b / S)]

    def estimate_k(self, k, alpha, n):
        kk_list = []
        for f in self.flavor_dict:
            ans = self.flavor_dict[f].get_counters()
            if ans[1] == 0:
                kk_list.append(1)
            else:
                kk_list.append(float(ans[0] / ans[1]))
        try:
            kk_list_min = min(kk_list)
            kk = kk_list_min * int(n)
        except:
            kk = k

        return alpha * kk + (1 - alpha) * k

    def estimate_k_avg(self, k, alpha, n):
        kk_list = []
        for f in self.flavor_dict:
            ans = self.flavor_dict[f].get_counters()
            if ans[1] == 0:
                kk_list.append(1)
            else:
                kk_list.append(float(ans[0] / ans[1]))
        num_of_over_line = 4
        out = os.popen("openstack flavor list |wc -l")
        num_of_system_flavor = int(out.read()) - num_of_over_line
        diff = num_of_system_flavor - len(self.flavor_dick)

        if diff > 0:
            l_to_add = [1] * diff
            kk_list.extend(l_to_add)
        elif diff < 0:
            for i in range(diff * -1):
                kk_list.remove(1)
        try:
            kk_list_mean = mean(kk_list)
            kk = kk_list_mean * int(n)
        except:
            kk = k

        return alpha * kk + (1 - alpha) * k




    def main(self):
        # read configuration
        config           = configparser.ConfigParser()
        config_name      = '/etc/nova/APSR_CONFIG.txt'
        config.read(config_name)
        epsilon          = float(config['DEFAULT']['EPSILON'])
        interval         = int(config['DEFAULT']['INTERVAL_SIZE'])
        type             = int(config['DEFAULT']['TYPE'])  # 0 - APSR 1- APSR AVG
        alpha            = float(config['DEFAULT']['ALPHA'])
        B                = float(config['DEFAULT']['BUDGET_SIZE'])
        max_s            = float(config['DEFAULT']['MAX_SCHDULERS'])
        self.s           = max_s
        APSR             = 0
        # get nuber of comput node
        out = os.popen("nova service-list |grep nova-compute |wc -l")
        output = out.read()
        N = int(output)
        print "Number of hosts is " + str(N)

        if N == 0:
            print "ERROR: Number of host is 0"
            self.LOG.info("APSR CONTROLLER: SLOT TIME: ERROR: Number of host is 0")
        else :
            print "APSR CONTROLLER is ready"

        B = float(B/100)*N
        K = N
        slot_num = 0

        while 1:
            self.update_dict_from_csv()

            if type == APSR:
                K = self.estimate_k(K, alpha, N)
            else:
                K = self.estimate_k_avg(K, alpha, N)

            [self.s, self.d] = self.max_parallizem(N, epsilon, B, K)

            f = open(self.shard_d, "w")
            f.write(str(int(self.d)))
            f.close()

            f = open(self.shard_s, "w")
            f.write(str(int(self.s)))
            f.close()

            slot_num += 1
            self.LOG.info("SLOT TIME: %d , estimate K : %d ,subsize group size (d) : %d ,num of schdulars : %d", slot_num, K,
                     self.d, self.s)
            print("SLOT TIME:" + str(slot_num) + ", estimate K : " + str(K) + " ,subsize group size (d) :" + str(
                self.d) + " ,num of schdulars : " + str(self.s))
            time.sleep(interval)  # in sec



def update_dict( flavor_id, filter_host_len):
    global apsr
    try:
        flavor_obj = apsr.flavor_dict[flavor_id]
    except:
        new_flavor = flavor(flavor_id)
        apsr.flavor_dict[flavor_id] = new_flavor
        flavor_obj = apsr.flavor_dict[flavor_id]

    apsr.counter += 1

    flavor_obj.update_counters(filter_host_len, apsr.d)
    apsr.flavor_dict.update({flavor_id: flavor_obj})

def get_d():
    f = open("/lib/python2.7/site-packages/nova/scheduler/shard_d.csv", "r")
    d = float(f.read())
    d= int (d)	
    f.close()
    return d

def get_s():
    f = open("/lib/python2.7/site-packages/nova/scheduler/shard_s.csv", "r")
    s = float(f.read())
    s= int(s)
    f.close()
    return s

def periodic_task():
    apsr = apsr_controller()
    apsr.main()

def open_s ():
    f1 = open("/lib/python2.7/site-packages/nova/scheduler/shard_s.csv", "r")
    f2 = open("/lib/python2.7/site-packages/nova/scheduler/shard_current_s.csv", "r")

    current_s = int(f2.readline())
    allow_s = int(f1.readline())
    ans = 0
    if (allow_s > current_s):
        f2 = open("/lib/python2.7/site-packages/nova/scheduler/shard_current_s.csv", "w")
        f2.write(str(current_s + 1))
        ans = 1

    f1.close()
    f2.close()
    #return 1
    return ans

def s_done ():
    f2 = open("/lib/python2.7/site-packages/nova/scheduler/shard_current_s.csv", "r")

    current_s = int(f2.readline())
    f2 = open("/lib/python2.7/site-packages/nova/scheduler/shard_current_s.csv", "w")
    f2.write(str(int(current_s - 1)))

    f2.close()

def update_dict_file( flavor_id, filter_host_len):
    f = open("/lib/python2.7/site-packages/nova/scheduler/shard_flavor_info.csv", "a")
    s = str(flavor_id) + "," + str(filter_host_len)
    f.write(s)
    f.close()
