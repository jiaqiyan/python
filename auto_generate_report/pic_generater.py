#!/usr/bin/python
# -*- coding:utf-8 -*-

import os,sys
import psutil
import threading
import matplotlib.pyplot as plt


'''
the main pylot module
params : data path, pic dpi
return : pic path
'''

# 锁
lock = threading.Lock()
BASE_PATH = os.path.abspath(os.path.dirname(__file__))
CPU_FILE = os.path.join(BASE_PATH, 'average_cpu.log')
class PylotMain(object):

    def __init__(self,data_path,cpu_cores,dpi=150):
        self.data_path = data_path
        self.cpu_cores = cpu_cores
        self.dpi = dpi
        if os.path.exists(CPU_FILE):
            os.remove(CPU_FILE)

    def check_isDigit(self, filed_str):
        strList=filed_str.split('.')
        if len(strList) == 1:
            if strList[0].isdigit():
                return 1
            else:
                print "%s is not a  numeric."%filed_str
                return 0
        elif len(strList) == 2:
            if strList[0].isdigit() and strList[1].isdigit() :
                return 1
            else:
                print "%s is not a  numeric."%filed_str
                return 0
        else:
            print "%s is not a  numeric."%filed_str
            return 0

    def _get_data_list(self):
        all_file_avg_cpu_list = {}
        all_file_avg_mem_sys_list = {}
        all_file_avg_mem_list = {}
        all_file_avg_mem_mu_list = {}
        result = []
        for path ,dirs ,files in os.walk(self.data_path):
            for file in files:
                if file.startswith("cpu_") and file.endswith(".log"):
                    one_file_avg_cpu_list = []
                    one_file_avg_mem_sys_list= []
                    file_mem_sys="MEM_" + '_'.join(file.split('_')[1:])
                    with open(os.path.join(path, file),'r') as f:

                        for line in f:
                            line = line.rstrip('\n').split()
                            if  self.check_isDigit(line[0]) and self.check_isDigit(line[8]):
                                cpu_field = float(line[8])
                                singlcore_cpu = cpu_field/self.cpu_cores
                                one_file_avg_cpu_list.append(singlcore_cpu)
                                one_file_avg_mem_sys_list.append(line[9])

                            else:
                                continue
                        all_file_avg_cpu_list[os.path.join(path, file)] = one_file_avg_cpu_list
                        all_file_avg_mem_sys_list[os.path.join(path, file_mem_sys)] = one_file_avg_mem_sys_list
                        cpu_size=len(one_file_avg_cpu_list)
                        cpu_sum=sum(one_file_avg_cpu_list)
                        cpu_average=cpu_sum/cpu_size
                        print file+" average cpu is "+ str(cpu_average)
                        with open(CPU_FILE, 'a') as cf:
                            cf.write('%s:%s\n' % (file, str(cpu_average)))
                elif file.startswith("jstat_") and file.endswith(".log"):
                    one_file_avg_mem_list = []
                    one_file_avg_mem_mu_list = []
                    file_mu= "MU_" + '_'.join(file.split('_')[1:])
                    with open(os.path.join(path, file) , 'r') as f:
                        lines = f.readlines()
                        for line in lines[1:]:
                            line = line.rstrip('\n').split()
                            mem_field = (float(line[2]) + float(line[3]) + float(line[5]) + float(line[7]) + float(line[11])) / (1024 * 1024)
                            one_file_avg_mem_list.append(mem_field)
                            sys_mem = round(((float(line[9])) / (1024 * 1024)), 2)
                            one_file_avg_mem_mu_list.append(sys_mem)
                        all_file_avg_mem_list[os.path.join(path, file)] = one_file_avg_mem_list
                        all_file_avg_mem_mu_list[os.path.join(path, file_mu)] = one_file_avg_mem_mu_list

        # print all_file_avg_cpu_list
        # print len(all_file_avg_cpu_list)
        return [all_file_avg_cpu_list,all_file_avg_mem_sys_list,all_file_avg_mem_list,all_file_avg_mem_mu_list]

    # 画图
    def draw_pic_and_save(self):
        global lock
        pic_data = self._get_data_list()
        for data_type in pic_data:
            for log in data_type:
                print log
                # print log,data_type[log]
                lock.acquire()
                # print "拿锁..."
                target_name = os.path.basename(log).split('_')[0]
                pic_name = os.path.basename(log).split('.')[0]
                data_len = len(data_type[log])
                x = [i for i in xrange(data_len)]
                y = data_type[log]
                if target_name == 'cpu':
                    plt.xlabel('time--per 5 seconds')
                    plt.ylabel('avg ' + target_name + '--%')
                elif target_name == 'MEM':
                    plt.xlabel('time--per 5 seconds')
                    plt.ylabel('avg sys mem '+ '--%')
                else:
                    plt.xlabel('time--per 5 seconds')
                    plt.ylabel('avg heap mem--GB')
                pic = plt.plot(x,y)
                plt.setp(pic ,linewidth=0.4)
                plt.grid(True)
                plt.savefig(log[:-4] + '.png' ,dpi=self.dpi)
                plt.close()
                print "saved:" + pic_name + ".png in " + log[:-4] + '.png'
                lock.release()
                # print "释放锁..."


if __name__ == '__main__':
    if not len(sys.argv) == 2 and not len(sys.argv) == 3:
        print '''
    error :
        example : ./pic_generater.py data_path(目标路径) [cpu核心数(可选)]
        '''
        sys.exit(1)
    data_path = sys.argv[1]
    if len(sys.argv) == 3:
        cores = int(sys.argv[2])
    else:
        cores = psutil.cpu_count()
    print "cores:",cores
    p = PylotMain(data_path,cpu_cores=cores)
    p.draw_pic_and_save()

