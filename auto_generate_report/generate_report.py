# coding=utf-8
from __future__ import division
import os
import re
import sys
import time
import base64
import argparse
import paramiko
from pyh import *

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
DRAW_PIC_SCRIPT = os.path.join(BASE_PATH, 'pic_generater.py')
HTML_FILE = os.path.join(BASE_PATH, 'report.html')
CPU_FILE = os.path.join(BASE_PATH, 'average_cpu.log')
ENV_FILE = os.path.join(BASE_PATH, 'test_env.txt')

def get_arguments():
    parser = argparse.ArgumentParser(prog='GenerateHtml')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument("--data_folder", help="the folder path which stores all the data files.", required=True)
    parser.add_argument("--core_num", help="core number.", required=False)
    args = parser.parse_args()
    return args

class ParseJTLFile:
    def __init__(self, data_folder):
        self.data_folder = data_folder
        self.jtl_list = self.search_jtl_file()

    def search_jtl_file(self):
        jtl_list = []
        for root, _, files in os.walk(self.data_folder):
            for new_file in files:
                if os.path.splitext(new_file)[1] == '.jtl':
                    jtl_list.append(os.path.join(root, new_file))
        return jtl_list

    def get_label_list(self, jtl_file):
        label_list = []
        with open(jtl_file) as f:
            for line in f.readlines():
                label = line.split(',')[2]
                if label not in label_list:
                    label_list.append(label)
        return label_list

    def get_sample_num(self, label, jtl_file):
        num = 0
        with open(jtl_file) as f:
            for line in f.readlines():
                if label:
                    if line.split(',')[2] == label:
                        num += 1
                else:
                    num += 1
        return num

    def get_average_value(self, label, jtl_file):
        num = 0
        total = 0
        with open(jtl_file) as f:
            for line in f.readlines():
                if label:
                    if line.split(',')[2] == label:
                        num += 1
                        total += int(line.split(',')[1])
                else:
                    num += 1
                    total += int(line.split(',')[1])
        average_value = int(total/num)
        return average_value

    def get_line_value_list(self, label, jtl_file):
        elapsed_list = []
        with open(jtl_file) as f:
            for line in f.readlines():
                if label:
                    if line.split(',')[2] == label:
                        elapsed_list.append(int(line.split(',')[1]))
                else:
                    elapsed_list.append(int(line.split(',')[1]))
        elapsed_list.sort()
        return elapsed_list


    def get_error_num(self, label, jtl_file):
        error_num = 0
        with open(jtl_file) as f:
            for line in f.readlines():
                if label:
                    if line.split(',')[2] == label and line.split(',')[7] != "true":
                        error_num += 1
                else:
                    if line.split(',')[7] != "true":
                        error_num += 1
        return error_num

    def get_timestamp_list(self, label, jtl_file):
        timestamp_list = []
        with open(jtl_file) as f:
            for line in f.readlines():
                if label:
                    if line.split(',')[2] == label:
                        timestamp_list.append(int(line.split(',')[0][:10]))
                else:
                    timestamp_list.append(int(line.split(',')[0][:10]))
        timestamp_list.sort()
        return timestamp_list

    def get_label_data(self, label, jtl_file):
        label_data = {}
        sample_num = self.get_sample_num(label, jtl_file)
        average_value = self.get_average_value(label, jtl_file)
        line_50_num = int(sample_num * 0.5)
        line_90_num = int(sample_num * 0.9)
        line_95_num = int(sample_num * 0.95)
        line_99_num = int(sample_num * 0.99)
        line_50_value = self.get_line_value_list(label, jtl_file)[line_50_num-1]
        line_90_value = self.get_line_value_list(label, jtl_file)[line_90_num-1]
        line_95_value = self.get_line_value_list(label, jtl_file)[line_95_num-1]
        line_99_value = self.get_line_value_list(label, jtl_file)[line_99_num-1]
        line_min_value = self.get_line_value_list(label, jtl_file)[0]
        line_max_value = self.get_line_value_list(label, jtl_file)[-1]
        error_num = self.get_error_num(label, jtl_file)
        error_rate = round(error_num/sample_num, 4) * 100
        timestamp_list = self.get_timestamp_list(label, jtl_file)
        start_timestamp = timestamp_list[0]
        end_timestamp = timestamp_list[-1]
        throughput = round(sample_num/(end_timestamp - start_timestamp), 1)
        label_data['sample'] = sample_num
        label_data['average'] = average_value
        label_data['median'] = line_50_value
        label_data['90'] = line_90_value
        label_data['95'] = line_95_value
        label_data['99'] = line_99_value
        label_data['min'] = line_min_value
        label_data['max'] = line_max_value
        label_data['error_rate'] = str(error_rate)+'%'
        label_data['throughput'] = str(throughput)+'/sec'
        return label_data

    def get_total_jtl_data(self):
        total_jtl_data = {}
        for jtl_file in self.jtl_list:
            jtl_data = {}
            label_list = self.get_label_list(jtl_file)
            for label in label_list:
                label_data = self.get_label_data(label, jtl_file)
                jtl_data[label] = label_data
            jtl_data['total'] = self.get_label_data('', jtl_file)
            total_jtl_data[jtl_file] = jtl_data
        return total_jtl_data


class BaseFunc:
    def __init__(self, data_folder, core_num):
        self.data_folder = data_folder
        self.core_num = core_num

    def draw_pic(self):
        rev = os.system('python %s %s %s' % (DRAW_PIC_SCRIPT, self.data_folder, self.core_num))
        if not rev:
            print "Generate png image successfully!"
        else:
            print "Generate png image fail!"
            sys.exit(1)

    def get_service_list(self):
        service_list = []
        for root, _, files in os.walk(self.data_folder):
            for new_file in files:
                if os.path.splitext(new_file)[1] == '.log':
                    try:
                        service_list.append(os.path.splitext(new_file)[0].split('_')[3])
                    except Exception as e:
                        print "Warning: %s" % os.path.join(root, new_file)
        return list(set(service_list))

    def get_thread_list(self):
        thread_list = []
        for root, _, files in os.walk(self.data_folder):
            for new_file in files:
                if os.path.splitext(new_file)[1] == '.log':
                    try:
                        thread_list.append(os.path.splitext(new_file)[0].split('_')[1])
                    except Exception as e:
                        print "Warning: %s" % os.path.join(root, new_file)
        return list(set(thread_list))

    def get_thread_service_file_dict(self):
        if not os.path.isdir(self.data_folder):
            print "%s: No such directory" % self.data_folder
            sys.exit(1)
        thread_list = self.get_thread_list()
        service_list = self.get_service_list()
        thread_service_file_dict = {}
        for thread in thread_list:
            service_file_dict = {}
            for service in service_list:
                log_file_list = []
                for root, _, files in os.walk(self.data_folder):
                    for new_file in files:
                        if os.path.splitext(new_file)[1] == '.png' and \
                            os.path.splitext(new_file)[0].split('_')[3] == service and \
                            os.path.splitext(new_file)[0].split('_')[1] == thread:
                            log_file_list.append(os.path.join(root, new_file))
                service_file_dict[service] = log_file_list
            thread_service_file_dict[int(thread)] = service_file_dict
        return thread_service_file_dict

class DrawHtmlPage:
    def __init__(self, thread_service_file_dict, total_jtl_data):
        self.thread_service_file_dict = thread_service_file_dict
        self.total_jtl_data = total_jtl_data

    def add_css_style(self):
        css_setting = {
            "body": {"font-family": ["Arial,", "Georgia,", "Serif,", "Sans-serif"], "font-size": ["12px"]},
            "p": { "margin": ["0"]},
            "table": {"border-collapse": ["collapse"]},
            "table, td, th": {"border": ["1px", "solid", "black"]},
            "td, th": {"padding": ["1px", "1px", "1px", "1px"], "text-align": ["center"]},
            "th": {"color": ["#000000"], "background-color": ["#63B8FF"]},
            "h2": {"color": ["#68228B"]}
        }
        css_tart = "<style type=\"text/css\">" + "\n"
        css_body = ""
        css_end = "</style>"
        selectors = css_setting.keys()
        for selector in selectors:
            css_dict = css_setting[selector]
            attributes = css_dict.keys()
            tmp_body = ""
            for attribute in attributes:
                tmp_body += attribute + ":" + " ".join(css_dict[attribute]) + ";"
            css_body += selector + "{" + tmp_body + "}" + "\n"
        css_style = css_tart + css_body + css_end
        return css_style

    def search_file_in_list(self, thread_files, pattern):
        get_file = ""
        for file_name in thread_files:
            if re.match(pattern, os.path.basename(file_name)):
                get_file = file_name
        return get_file

    def convert_image_to_base64(self, png_file):
        with open(png_file, 'rb') as image_file:
            image_str = base64.b64encode(image_file.read())
        return image_str

    def get_jtl_file_by_thread(self, thread):
        jtl_file_name = ''
        jtl_list = self.total_jtl_data.keys()
        for jtl_file in jtl_list:
            if jtl_file.endswith('_%s.jtl' % thread):
                jtl_file_name = jtl_file
                break
        return jtl_file_name

    def get_cpu_rate(self):
        cpu_data = {}
        thread_list = self.thread_service_file_dict.keys()
        for thread in thread_list:
            service_list = self.thread_service_file_dict[thread].keys()
            for service in service_list:
                service_data = {}
                with open(CPU_FILE) as f:
                    for line in f.readlines():
                        file_name = line.split(':')[0]
                        if file_name.split('_')[1] == str(thread) and file_name.split('_')[3][:-4] == service:
                            service_data[service] = line.split(':')[1][:-1]
                            break
            cpu_data[thread] = service_data
        return cpu_data

    def generate_test_env(self, indicator):
        count = 1
        indicator << h1('一、测试环境')
        with open(ENV_FILE) as f:
            for line in f.readlines():
                indicator << h3('(%d) %s' % (count, line[:-1]))
                count += 1
        indicator << br()

    def generate_test_result(self, indicator):
        cpu_data = self.get_cpu_rate()
        print cpu_data
        indicator << h1('二、测试结果')
        result_table = indicator << table(id='result')
        result_th = result_table << tr()
        result_th << th('线程数') + th('吞吐量(/sec)') + th('平均响应时间(ms)') + \
                    th('90%响应时间(ms)') + th('95%响应时间(ms)') + th('最大响应时间(ms)')
        cpu_service_list = cpu_data.values()[0].keys()
        cpu_service_list.sort()
        for service in cpu_service_list:
            result_th << th(str(service) + ' CPU利用率(%)')
        thread_list = self.thread_service_file_dict.keys()
        thread_list.sort()
        for thread in thread_list:
            jtl_file = self.get_jtl_file_by_thread(thread)
            jtl_data = self.total_jtl_data[jtl_file]['total']
            result_tr = result_table << tr()
            result_tr << td(thread) + td(jtl_data['throughput']) + td(jtl_data['average']) + \
                        td(jtl_data['90']) + td(jtl_data['95']) + td(jtl_data['max'])
            cpu_service_data_list = cpu_data[thread].keys()
            cpu_service_data_list.sort()
            for cpu_service in cpu_service_data_list:
                result_tr << td(round(float(cpu_data[thread][cpu_service]), 2))

    def generate_performance_curve(self, indicator):
        indicator << h1('三、性能测试曲线')
        thread_list = self.thread_service_file_dict.keys()
        thread_list.sort()
        print self.thread_service_file_dict
        for thread in thread_list:
            label_list = []
            seq = 2
            thread_title = indicator << div(id='thread')
            thread_title << h2('< %s 个线程 >' % thread)
            indicator << h3('[1] 吞吐量')
            jtl_table = indicator << table(id='jtl_table')
            jtl_file = self.get_jtl_file_by_thread(thread)
            print jtl_file
            if jtl_file:
                jtl_tr_th = jtl_table << tr()
                jtl_tr_th << th('Label') + th('#Samples') + th('Average') + th('Median') + th('90% Line') \
                        + th('95% Line') + th('99% Line') + th('Min') + th('Max') + th('Error%') + th('Throughput')
                for label, label_data in self.total_jtl_data[jtl_file].items():
                    if label != 'total':
                        jtl_tr_td = jtl_table << tr()
                        jtl_tr_td << td(label) + td(label_data['sample']) + td(label_data['average']) + td(label_data['median'])\
                        + td(label_data['90']) + td(label_data['95']) + td(label_data['99']) + td(label_data['min'])\
                        + td(label_data['max']) + td(label_data['error_rate']) + td(label_data['throughput'])
                jtl_tr_td = jtl_table << tr()
                jtl_data = self.total_jtl_data[jtl_file]['total']
                jtl_tr_td << td('总体') + td(jtl_data['sample']) + td(jtl_data['average']) + td(jtl_data['median'])\
                    + td(jtl_data['90']) + td(jtl_data['95']) + td(jtl_data['99']) + td(jtl_data['min'])\
                    + td(jtl_data['max']) + td(jtl_data['error_rate']) + td(jtl_data['throughput'])
            indicator << br()
            service_list = self.thread_service_file_dict[thread].keys()
            service_list.sort()
            for service in service_list:
                service_title = indicator << div(id='service')
                service_title << h3('[%d] %s曲线' % (seq, service))
                log_files = self.thread_service_file_dict[thread][service]
                print log_files
                cpu_png_file = self.search_file_in_list(log_files, 'cpu.+png')
                jstat_png_file = self.search_file_in_list(log_files, 'jstat.+png')
                indicator << p('CPU')
                indicator << img(src='data:image/png;base64,%s'%self.convert_image_to_base64(cpu_png_file),width="600", height="400")
                indicator << p('Heap')
                indicator << img(src='data:image/png;base64,%s'%self.convert_image_to_base64(jstat_png_file),width="600", height="400")
                seq += 1

    def upload_html(self):
        now = int(time.time())
        t = paramiko.Transport(("192.168.80.26",22))
        t.connect(username = "www-data", password = "Ele@777")
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.mkdir('/var/www/html/results/%d' % now)
        remotepath = '/var/www/html/results/%d/report.html' % now
        localpath = HTML_FILE
        sftp.put(localpath, remotepath)
        t.close()
        print "Report URL: http://192.168.80.26/results/%d/report.html" % now

    def generate_html_page(self):
        page = PyH('Performance Test Report')
        page << div("%s" % self.add_css_style())
        self.generate_test_env(page)
        self.generate_test_result(page)
        self.generate_performance_curve(page)
        page.printOut(HTML_FILE)
        self.upload_html()

def main():
    args = get_arguments()
    if args.core_num:
        core_num = args.core_num
    else:
        core_num = ""
    base_func = BaseFunc(args.data_folder, core_num)
    base_func.draw_pic()
    thread_service_file_dict = base_func.get_thread_service_file_dict()
    pasre_jtl_file = ParseJTLFile(args.data_folder)
    total_jtl_data = pasre_jtl_file.get_total_jtl_data()
    draw_html_page = DrawHtmlPage(thread_service_file_dict, total_jtl_data)
    draw_html_page.generate_html_page()

if __name__ == "__main__":
    main()
